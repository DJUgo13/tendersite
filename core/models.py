from django.contrib.auth.models import User
from django.db import models
from django.db.models import Q
from django.utils import timezone
from django.core.exceptions import ValidationError

# Расширение модели User для ролей
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Администратор'),
        ('manager', 'Менеджер'),
        ('leadership', 'Руководство'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name='Пользователь')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='manager', verbose_name='Роль')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
    
    class Meta:
        verbose_name = 'Профиль пользователя'
        verbose_name_plural = 'Профили пользователей'
    
    def is_admin(self):
        return self.role == 'admin'
    
    def is_manager(self):
        return self.role == 'manager'
    
    def is_leadership(self):
        return self.role == 'leadership'

# Модель Транспортной компании (заказчик)
class Company(models.Model):
    inn = models.CharField(max_length=12, unique=True, verbose_name='ИНН')
    name = models.CharField(max_length=255, verbose_name='Название компании')
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='Пользователь')  # Связь с логином
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Компания'
        verbose_name_plural = 'Компании'

# Модель Тендера (аукциона)
class Tender(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Черновик'),
        ('open', 'Идёт приём ставок'),
        ('closed', 'Завершён'),
    ]
    name = models.CharField(max_length=255, verbose_name='Название тендера')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    admin = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Администратор', related_name='tenders')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft', verbose_name='Статус')
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='Время начала торгов')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='Время окончания торгов')
    # Настраиваемый финальный таймер (в минутах)
    final_timer_minutes = models.PositiveIntegerField(default=10, verbose_name='Финальный таймер (минуты)', 
                                                      help_text='Время без новых ставок до автоматического закрытия направления')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    class Meta:
        verbose_name = 'Тендер'
        verbose_name_plural = 'Тендеры'

# Модель Направления в рамках тендера (например, Сочи - 5 машин)
class Direction(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='directions', verbose_name='Тендер')
    city_name = models.CharField(max_length=100, verbose_name='Город назначения')
    volume = models.PositiveIntegerField(verbose_name='Количество машин (объём)')
    start_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Стартовая цена')
    current_best_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Текущая лучшая цена')
    winner = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='won_directions', verbose_name='Победитель')
    final_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Финальная цена (цена победителя)')
    # Для переторжки и финального таймера
    last_bid_time = models.DateTimeField(null=True, blank=True, verbose_name='Время последней ставки')
    final_timer_end = models.DateTimeField(null=True, blank=True, verbose_name='Окончание финального таймера')
    is_in_rebidding = models.BooleanField(default=False, verbose_name='Идёт переторжка')
    rebidding_end_time = models.DateTimeField(null=True, blank=True, verbose_name='Окончание переторжки')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.city_name} - {self.volume} маш. (старт: {self.start_price} руб.)"

    class Meta:
        verbose_name = 'Направление'
        verbose_name_plural = 'Направления'

# САМАЯ ВАЖНАЯ МОДЕЛЬ - Ставка компании по направлению
class Bid(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, verbose_name='Тендер')
    direction = models.ForeignKey(Direction, on_delete=models.CASCADE, related_name='bids', verbose_name='Направление')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, verbose_name='Компания')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена ставки')
    created_at = models.DateTimeField(auto_now_add=True)
    # Поле для аудита - кто сделал ставку (менеджер компании)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Пользователь, создавший ставку')
    # Поле для отслеживания активности ставки
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        verbose_name = 'Ставка'
        verbose_name_plural = 'Ставки'
        constraints = [
            # Одна АКТИВНАЯ ставка на направление в тендере от компании
            models.UniqueConstraint(
                fields=['tender', 'direction', 'company'],
                condition=Q(is_active=True),
                name='unique_active_bid_per_direction_company',
            )
        ]
        indexes = [
            models.Index(fields=['tender', 'direction', 'company', '-created_at']),
            models.Index(fields=['direction', 'is_active', 'price']),
        ]

    def __str__(self):
        return f"{self.company}: {self.price} руб. за {self.direction.city_name}"

# Модель для аудит-логов
class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('tender_created', 'Создан тендер'),
        ('tender_opened', 'Открыт тендер'),
        ('tender_closed', 'Закрыт тендер'),
        ('bid_created', 'Создана ставка'),
        ('bid_updated', 'Обновлена ставка'),
        ('direction_created', 'Создано направление'),
        ('company_created', 'Создана компания'),
        ('user_login', 'Вход в систему'),
        ('user_logout', 'Выход из системы'),
        ('report_generated', 'Сгенерирован отчёт'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Пользователь')
    action = models.CharField(max_length=50, choices=ACTION_CHOICES, verbose_name='Действие')
    object_type = models.CharField(max_length=50, verbose_name='Тип объекта')
    object_id = models.PositiveIntegerField(null=True, blank=True, verbose_name='ID объекта')
    details = models.JSONField(default=dict, blank=True, verbose_name='Детали')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP адрес')
    user_agent = models.TextField(blank=True, null=True, verbose_name='User Agent')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время')
    
    class Meta:
        verbose_name = 'Аудит лог'
        verbose_name_plural = 'Аудит логи'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.user} - {self.timestamp}"

# Модель для победителей (для истории)
class Winner(models.Model):
    tender = models.ForeignKey(Tender, on_delete=models.CASCADE, related_name='winners', verbose_name='Тендер')
    direction = models.ForeignKey(Direction, on_delete=models.CASCADE, related_name='winners_history', verbose_name='Направление')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='wins', verbose_name='Компания')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    final_timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время определения победителя')
    
    class Meta:
        verbose_name = 'Победитель'
        verbose_name_plural = 'Победители'
        unique_together = ('tender', 'direction')
    
    def __str__(self):
        return f"{self.company.name} - {self.direction.city_name} - {self.price} ₽"