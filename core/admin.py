from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.contrib import messages
from .models import Company, Tender, Direction, Bid, UserProfile, AuditLog, Winner
from .utils import send_tender_started_emails

# Настройка отображения модели Тендер в админке
class DirectionInline(admin.TabularInline):
    model = Direction
    extra = 1  # Количество пустых форм для добавления направлений

@admin.register(Tender)
class TenderAdmin(admin.ModelAdmin):
    list_display = ('name', 'admin', 'status', 'start_time', 'created_at', 'close_tender_button')
    list_filter = ('status',)
    inlines = [DirectionInline] 
    
    def close_tender_button(self, obj):
        if obj.status == 'draft':
            open_url = f'/core/admin/tender/{obj.id}/open/'
            return format_html(
                '<a class="button" href="{}" style="background-color: #0d6efd; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px; display: inline-block;">Открыть тендер</a>',
                open_url
            )
        if obj.status == 'open':
            close_url = f'/core/admin/tender/{obj.id}/close/'
            return format_html(
                '<a class="button" href="{}" style="background-color: #417690; color: white; padding: 10px 15px; text-decoration: none; border-radius: 4px; display: inline-block;">Закрыть тендер</a>',
                close_url
            )
        elif obj.status == 'closed':
            report_url = f'/core/admin/tender/{obj.id}/report/'
            pdf_url = f'/core/admin/tender/{obj.id}/protocol-pdf/'
            return format_html(
                '<span style="color: #28a745;">Завершён</span> | <a href="{}" style="color: #417690;">Excel</a> | <a href="{}" style="color: #417690;">PDF</a>',
                report_url,
                pdf_url
            )
        return '-'
    close_tender_button.short_description = 'Действие'

    def save_model(self, request, obj, form, change):
        is_opening = False
        if change:
            old_obj = Tender.objects.get(pk=obj.pk)
            if old_obj.status != 'open' and obj.status == 'open':
                is_opening = True
                if not obj.start_time:
                    obj.start_time = timezone.now()
        elif obj.status == 'open':
            # Create new tender directly in 'open' status
            is_opening = True
            if not obj.start_time:
                obj.start_time = timezone.now()

        super().save_model(request, obj, form, change)

        if is_opening:
            results = send_tender_started_emails(obj)
            ok = sum(1 for r in results if r['success'])
            messages.info(request, f"Тендер открыт. Отправлено уведомлений: {ok}.")

# Регистрация остальных моделей с базовой настройкой
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'inn', 'user', 'created_at')
    search_fields = ('name', 'inn')

@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    list_display = ('city_name', 'tender', 'volume', 'start_price', 'current_best_price')
    list_filter = ('tender',)

@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ('company', 'direction', 'price', 'created_at')
    list_filter = ('tender', 'direction')
    readonly_fields = ('created_at',)  # Запрещаем редактирование времени создания

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'created_at')
    list_filter = ('role',)
    search_fields = ('user__username', 'user__email')

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('action', 'user', 'object_type', 'object_id', 'timestamp', 'ip_address')
    list_filter = ('action', 'object_type', 'timestamp')
    search_fields = ('user__username', 'object_type', 'details')
    readonly_fields = ('timestamp', 'ip_address', 'user_agent', 'details')
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False  # Логи создаются только автоматически

@admin.register(Winner)
class WinnerAdmin(admin.ModelAdmin):
    list_display = ('company', 'tender', 'direction', 'price', 'final_timestamp')
    list_filter = ('tender', 'final_timestamp')
    search_fields = ('company__name', 'tender__name', 'direction__city_name')
    readonly_fields = ('final_timestamp',)

# Регистрируем кастомные настройки для админки
admin.site.site_header = 'Панель администратора Тендерной площадки'
admin.site.index_title = 'Управление системой'