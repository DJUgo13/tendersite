"""
Утилиты для работы с ролями, аудитом и бизнес-логикой
"""
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.core.mail import EmailMultiAlternatives, get_connection
from django.conf import settings
from .models import UserProfile, AuditLog, Direction, Bid, Tender, Company, Winner
import logging

logger = logging.getLogger(__name__)


def get_user_role(user):
    """Получить роль пользователя"""
    if not user or not user.is_authenticated:
        return None
    
    try:
        profile = user.profile
        return profile.role
    except (UserProfile.DoesNotExist, AttributeError):
        # Если профиля нет, проверяем is_staff для обратной совместимости
        if user.is_staff:
            return 'admin'
        return 'manager'
    except Exception as e:
        # На случай других ошибок (например, таблица не создана или миграции не применены)
        # Используем обратную совместимость
        if user.is_staff:
            return 'admin'
        return 'manager'


def is_admin(user):
    """Проверка, является ли пользователь администратором"""
    return get_user_role(user) == 'admin'


def is_manager(user):
    """Проверка, является ли пользователь менеджером"""
    return get_user_role(user) == 'manager'


def is_leadership(user):
    """Проверка, является ли пользователь руководством"""
    return get_user_role(user) == 'leadership'


def log_action(user, action, object_type, object_id=None, details=None, request=None):
    """
    Логирование действия пользователя
    
    Args:
        user: Пользователь, выполнивший действие
        action: Тип действия (из AuditLog.ACTION_CHOICES)
        object_type: Тип объекта (например, 'tender', 'bid')
        object_id: ID объекта
        details: Дополнительные детали (dict)
        request: HTTP запрос (для получения IP и User-Agent)
    """
    ip_address = None
    user_agent = None
    
    if request:
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
    
    AuditLog.objects.create(
        user=user if user.is_authenticated else None,
        action=action,
        object_type=object_type,
        object_id=object_id,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent
    )


def get_client_ip(request):
    """Получить IP адрес клиента из запроса"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip



def check_and_handle_rebidding(direction):
    """
    Проверка и обработка переторжки при равных ценах
    
    Returns:
        bool: True если началась или продолжается переторжка, False если нет
    """
    if direction.tender.status != 'open':
        return False
    
    # Получаем все активные ставки по направлению
    active_bids = direction.bids.filter(is_active=True).order_by('price', 'created_at')
    
    if active_bids.count() < 2:
        # Если была переторжка, но ставки исчезли (теоретически), сбрасываем флаг
        if direction.is_in_rebidding:
            direction.is_in_rebidding = False
            direction.rebidding_end_time = None
            direction.save(update_fields=['is_in_rebidding', 'rebidding_end_time'])
        return False
    
    # Проверяем, есть ли равные минимальные цены
    min_price = active_bids.first().price
    equal_bids = active_bids.filter(price=min_price)
    
    if equal_bids.count() >= 2:
        if not direction.is_in_rebidding:
            # Начинаем переторжку
            direction.is_in_rebidding = True
            direction.rebidding_end_time = timezone.now() + timedelta(minutes=5)  # 5 минут на переторжку
            direction.final_timer_end = None  # КРИТИЧНО: Убираем обычный таймер
            direction.save(update_fields=['is_in_rebidding', 'rebidding_end_time', 'final_timer_end'])
            return True
        return True # Продолжаем переторжку
    else:
        # Равенства больше нет (кто-то перебил ниже)
        if direction.is_in_rebidding:
            direction.is_in_rebidding = False
            direction.rebidding_end_time = None
            # Мы не сохраняем здесь final_timer_end, так как update_final_timer будет вызван следом
            direction.save(update_fields=['is_in_rebidding', 'rebidding_end_time'])
            return False
    
    return False


def update_final_timer(direction):
    """
    Обновление финального таймера для направления
    Вызывается при каждой новой ставке
    """
    if direction.tender.status != 'open':
        return
    
    # Если наступила переторжка, таймер "одной минуты" не работает
    if direction.is_in_rebidding:
        return
    
    timer_minutes = direction.tender.final_timer_minutes
    direction.last_bid_time = timezone.now()
    direction.final_timer_end = timezone.now() + timedelta(minutes=timer_minutes)
    direction.save(update_fields=['last_bid_time', 'final_timer_end'])


def initialize_direction_timers(tender):
    """
    Устанавливает начальный финальный таймер для всех направлений тендера.
    Вызывается при открытии тендера.
    """
    now = timezone.now()
    timer_minutes = tender.final_timer_minutes
    
    # Обновляем все направления тендера, у которых ещё нет таймера
    directions = tender.directions.filter(final_timer_end__isnull=True)
    for d in directions:
        d.final_timer_end = now + timedelta(minutes=timer_minutes)
        d.save(update_fields=['final_timer_end'])
    
    logger.info(f"Initialized timers for {directions.count()} directions in Tender {tender.id}")


def check_auto_close_directions():
    """
    Проверка и автоматическое закрытие направлений по таймеру.
    Если все направления тендера закрыты, закрывает сам тендер.
    """
    now = timezone.now()

    # 1. Завершаем переторжку по времени
    rebidding_ended = Direction.objects.filter(
        tender__status='open',
        is_in_rebidding=True,
        rebidding_end_time__isnull=False,
        rebidding_end_time__lte=now
    )
    
    for d in rebidding_ended:
        d.is_in_rebidding = False
        d.rebidding_end_time = None
        # Если переторжка закончилась, закрываем направление (ставим таймер на сейчас)
        d.final_timer_end = now
        d.save(update_fields=['is_in_rebidding', 'rebidding_end_time', 'final_timer_end'])
    
    # 2. Находим направления с истёкшим таймером, которые ещё не закрыты (winner=None)
    # Важно: обрабатываем все направления тендеров со статусом 'open'
    directions_to_close = Direction.objects.filter(
        tender__status='open',
        final_timer_end__lte=now,
        winner__isnull=True
    )
    
    affected_tenders = set()
    for direction in directions_to_close:
        affected_tenders.add(direction.tender)
        
        # Определяем победителя
        winning_bid = direction.bids.filter(is_active=True).order_by('price', 'created_at').first()
        
        if winning_bid:
            direction.winner = winning_bid.company
            direction.final_price = winning_bid.price
            direction.current_best_price = winning_bid.price
            direction.save()
            
            # Создаём запись в Winner
            from .models import Winner
            winner_record, created = Winner.objects.update_or_create(
                tender=direction.tender,
                direction=direction,
                defaults={
                    'company': winning_bid.company,
                    'price': winning_bid.price
                }
            )
            # Отправляем письмо немедленно, если результат зафиксирован впервые
            if created:
                send_winner_email(direction.tender, direction, winning_bid)
        else:
            # Направление закрывается без победителя (никто не сделал ставку)
            # Оно всё равно будет считаться завершённым в цикле ниже
            pass

    # 3. Проверяем затронутые тендеры: если ВСЕ направления тендера имеют winner ИЛИ их таймер истёк
    open_tenders = Tender.objects.filter(status='open')
    for tender in open_tenders:
        all_finished = True
        for d in tender.directions.all():
            # Направление считается законченным если:
            # - есть победитель
            # - ИЛИ таймер истёк и ставок нет
            is_finished = (d.winner is not None) or (d.final_timer_end and d.final_timer_end <= now)
            if not is_finished:
                all_finished = False
                break
        
        if all_finished:
            logger.info(f"Auto-closing Tender {tender.id} because all directions are finished.")
            from .views import close_tender_and_notify_winners
            close_tender_and_notify_winners(tender, set_end_time=True)


def get_anonymous_best_price(direction, user_company=None):
    """
    Получить анонимную лучшую цену для отображения
    Показывает только цену, без названия компании
    """
    best_bid = direction.bids.filter(is_active=True).order_by('price', 'created_at').first()
    
    if not best_bid:
        return {
            'price': direction.start_price,
            'is_user_bid': False,
            'position': None
        }
    
    # Проверяем, является ли это ставкой пользователя
    is_user_bid = user_company and best_bid.company == user_company
    
    # Определяем позицию (если это не ставка пользователя)
    if not is_user_bid:
        all_bids = direction.bids.filter(is_active=True).order_by('price', 'created_at')
        position = list(all_bids.values_list('id', flat=True)).index(best_bid.id) + 1
    else:
        position = None
    
    return {
        'price': best_bid.price,
        'is_user_bid': is_user_bid,
        'position': position,
        'display_text': f"Лучшая: {best_bid.price} ₽" if not is_user_bid else f"Ваша ставка: {best_bid.price} ₽"
    }


def send_winner_email(tender, direction, winning_bid):
    """Отправка письма победителю лота через Celery."""
    logger.info(f"Queueing winner email for Tender {tender.id}, Direction {direction.id}, Company {winning_bid.company.id}")
    
    try:
        from .tasks import send_winner_email_task
        async_result = send_winner_email_task.delay(tender.id, direction.id, winning_bid.id)
        return True, f"Отправка письма победителю {winning_bid.company.name} поставлена в очередь (task_id={async_result.id})"
    except Exception as e:
        logger.exception("Failed to enqueue winner email task")
        return False, f"Ошибка постановки в очередь: {e}"


def send_tender_started_emails(tender, site_url=None):
    """
    Email всем потенциальным участникам о старте тендера.
    Отправка происходит через Celery (асинхронно).
    """
    logger.info(f"Queueing start emails for Tender {tender.id}")
    # Считаем “сколько уйдёт” быстро (для вывода в UI), а сами письма шлём таской.
    recipients_qs = (
        User.objects.filter(is_active=True)
        .exclude(email__isnull=True)
        .exclude(email='')
        .values('email')
        .distinct()
    )
    queued = recipients_qs.count()

    try:
        from .tasks import send_tender_started_emails_task
        async_result = send_tender_started_emails_task.delay(tender.id, site_url=site_url or settings.SITE_URL)
        return {
            'queued': queued,
            'task_id': getattr(async_result, 'id', None),
            'message': f'Отправка {queued} писем поставлена в очередь (Celery)'
        }
    except Exception as e:
        logger.exception("Failed to enqueue Celery task for tender started emails")
        return {'queued': queued, 'task_id': None, 'message': f'Не удалось поставить рассылку в очередь: {e}'}
