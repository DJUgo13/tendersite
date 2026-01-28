"""
Утилиты для работы с ролями, аудитом и бизнес-логикой
"""
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from .models import UserProfile, AuditLog, Direction, Bid, Tender, Company, Winner


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
        bool: True если началась переторжка, False если нет
    """
    if direction.tender.status != 'open':
        return False
    
    # Получаем все активные ставки по направлению
    active_bids = direction.bids.filter(is_active=True).order_by('price', 'created_at')
    
    if active_bids.count() < 2:
        return False
    
    # Проверяем, есть ли равные минимальные цены
    min_price = active_bids.first().price
    equal_bids = active_bids.filter(price=min_price)
    
    if equal_bids.count() >= 2 and not direction.is_in_rebidding:
        # Начинаем переторжку
        direction.is_in_rebidding = True
        direction.rebidding_end_time = timezone.now() + timedelta(minutes=5)  # 5 минут на переторжку
        direction.save()
        
        # Уведомляем компании о переторжке (можно добавить email)
        return True
    
    return False


def update_final_timer(direction):
    """
    Обновление финального таймера для направления
    Вызывается при каждой новой ставке
    """
    if direction.tender.status != 'open':
        return
    
    timer_minutes = direction.tender.final_timer_minutes
    direction.last_bid_time = timezone.now()
    direction.final_timer_end = timezone.now() + timedelta(minutes=timer_minutes)
    direction.save()


def check_auto_close_directions():
    """
    Проверка и автоматическое закрытие направлений по таймеру
    Вызывается периодически (через cron или celery)
    """
    now = timezone.now()

    # Завершаем переторжку, если время вышло
    Direction.objects.filter(
        tender__status='open',
        is_in_rebidding=True,
        rebidding_end_time__isnull=False,
        rebidding_end_time__lte=now
    ).update(is_in_rebidding=False, rebidding_end_time=None)
    
    # Находим направления с истёкшим таймером
    directions_to_close = Direction.objects.filter(
        tender__status='open',
        final_timer_end__lte=now,
        winner__isnull=True
    )
    
    for direction in directions_to_close:
        # Определяем победителя
        winning_bid = direction.bids.filter(is_active=True).order_by('price', 'created_at').first()
        
        if winning_bid:
            direction.winner = winning_bid.company
            direction.final_price = winning_bid.price
            direction.current_best_price = winning_bid.price
            direction.save()
            
            # Создаём запись в Winner
            from .models import Winner
            Winner.objects.update_or_create(
                tender=direction.tender,
                direction=direction,
                defaults={
                    'company': winning_bid.company,
                    'price': winning_bid.price
                }
            )


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
    """Отправка письма победителю лота."""
    try:
        user_email = winning_bid.company.user.email
        if not user_email:
            return False, f'У победителя {winning_bid.company.name} не указан email'
        
        subject = f'{settings.EMAIL_SUBJECT_PREFIX}Победа в тендере "{tender.name}"'
        text_message = f'''Поздравляем! Ваша компания "{winning_bid.company.name}" победила в тендере "{tender.name}".

Детали победы:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Тендер: {tender.name}
Направление: {direction.city_name}
Ваша выигрышная ставка: {winning_bid.price:,.2f} руб.
Объём: {direction.volume} машин
Дата закрытия тендера: {tender.end_time.strftime("%d.%m.%Y %H:%M") if tender.end_time else "Не указана"}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

С вами свяжутся в ближайшее время для уточнения деталей и оформления договора.

С уважением,
Команда тендерной площадки'''
        
        html_message = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #28a745; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                .details {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #28a745; }}
                .detail-row {{ margin: 10px 0; }}
                .detail-label {{ font-weight: bold; color: #555; }}
                .detail-value {{ color: #28a745; font-size: 1.1em; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 0.9em; }}
                .price {{ font-size: 1.3em; font-weight: bold; color: #28a745; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1> Поздравляем с победой!</h1>
                </div>
                <div class="content">
                    <p>Ваша компания <strong>"{winning_bid.company.name}"</strong> победила в тендере <strong>"{tender.name}"</strong>!</p>
                    
                    <div class="details">
                        <div class="detail-row">
                            <span class="detail-label">Тендер:</span>
                            <span class="detail-value">{tender.name}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Направление:</span>
                            <span class="detail-value">{direction.city_name}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Ваша выигрышная ставка:</span>
                            <span class="detail-value price">{winning_bid.price:,.2f} руб.</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Объём:</span>
                            <span class="detail-value">{direction.volume} машин</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Дата закрытия тендера:</span>
                            <span class="detail-value">{tender.end_time.strftime("%d.%m.%Y %H:%M") if tender.end_time else "Не указана"}</span>
                        </div>
                    </div>
                    
                    <p style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin-top: 20px;">
                        <strong>Важно:</strong> С вами свяжутся в ближайшее время для уточнения деталей и оформления договора.
                    </p>
                </div>
                <div class="footer">
                    <p>С уважением,<br>Команда тендерной площадки</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user_email],
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        
        return True, f'Письмо отправлено победителю {winning_bid.company.name} ({user_email})'
    except Exception as e:
        return False, f'Ошибка отправки победителю {tender.name}: {e}'


def send_tender_started_emails(tender):
    """
    Email всем потенциальным участникам о старте тендера.
    """
    subject = f'{settings.EMAIL_SUBJECT_PREFIX}Старт тендера "{tender.name}"'

    text_message = f'''Открыт тендер: {tender.name}
Статус: {tender.get_status_display()}
Количество направлений: {tender.directions.count()}

Перейдите в систему для участия.
'''

    html_message = f'''
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif; color: #333;">
        <div style="max-width: 650px; margin: 0 auto; padding: 20px;">
            <h2 style="margin: 0 0 12px 0;"> Открыт тендер: {tender.name}</h2>
            <p style="margin: 0 0 10px 0;">Статус: <strong>{tender.get_status_display()}</strong></p>
            <p style="margin: 0 0 10px 0;">Направлений: <strong>{tender.directions.count()}</strong></p>
            <p style="margin: 16px 0 0 0;">Войдите в систему и сделайте ставку по интересующим направлениям.</p>
        </div>
    </body>
    </html>
    '''

    recipients = set()
    all_users_with_email = User.objects.filter(is_active=True).exclude(email='').values_list('email', flat=True)
    for email in all_users_with_email:
        if email:
            recipients.add(email)

    results = []
    for email in recipients:
        email = email.strip()
        try:
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
            )
            msg.attach_alternative(html_message, "text/html")
            msg.send(fail_silently=False)
            results.append({'email': email, 'success': True, 'message': f'OK: {email}'})
        except Exception as e:
            results.append({'email': email, 'success': False, 'message': f'ERR: {email} — {e}'})

    return results
