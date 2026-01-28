"""
Views для панели руководства (только просмотр)
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Count, Sum
from django.db.models.functions import ExtractYear, ExtractMonth
from datetime import timedelta
from .models import Tender, Winner, AuditLog
from .decorators import leadership_required
from .utils import get_user_role, is_admin, log_action
from django.contrib import messages
from . import views as core_views
import json
from .models import Direction


@leadership_required
@login_required
def leadership_dashboard(request):
    """Панель руководства - просмотр отчётов и статистики"""
    # Получаем все закрытые тендеры
    closed_tenders = Tender.objects.filter(status='closed').order_by('-end_time', '-created_at')
    
    # Статистика за последние 30 дней
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_tenders = closed_tenders.filter(end_time__gte=thirty_days_ago)
    
    # Общая статистика
    total_tenders = closed_tenders.count()
    total_winners = Winner.objects.filter(tender__status='closed').count()
    
    context = {
        'closed_tenders': closed_tenders[:20],  # Последние 20
        'recent_tenders': recent_tenders,
        'total_tenders': total_tenders,
        'total_winners': total_winners,
        'stats_period': 30,
    }
    
    return render(request, 'core/leadership_dashboard.html', context)


@leadership_required
@login_required
def leadership_tender_detail(request, tender_id):
    """Детали тендера для руководства"""
    tender = get_object_or_404(Tender, id=tender_id)
    directions = tender.directions.all()
    winners = Winner.objects.filter(tender=tender)
    
    context = {
        'tender': tender,
        'directions': directions,
        'winners': winners,
    }
    
    return render(request, 'core/leadership_tender_detail.html', context)


@leadership_required
@login_required
def leadership_tender_report(request, tender_id):
    """Excel отчёт для руководства."""
    tender = get_object_or_404(Tender, id=tender_id)
    log_action(request.user, 'report_generated', 'tender', tender.id, {'type': 'excel'}, request)
    return core_views._build_tender_excel_response(tender)


@leadership_required
@login_required
def leadership_tender_matrix_report(request, tender_id):
    """
    Сводная таблица (Matrix Excel) для руководства.
    Заменяет старый PDF протокол.
    """
    tender = get_object_or_404(Tender, id=tender_id)
    log_action(request.user, 'report_generated', 'tender', tender.id, {'type': 'matrix_excel'}, request)
    return core_views._build_tender_matrix_excel_response(tender)


@leadership_required
@login_required
def leadership_statistics(request):
    """Статистика по тендерам по годам и месяцам"""
    # Получаем все закрытые тендеры
    closed_tenders_qs = Tender.objects.filter(status='closed')
    
    # Получаем доступные года для фильтра
    available_years = closed_tenders_qs.annotate(
        year=ExtractYear('end_time')
    ).values_list('year', flat=True).distinct().order_by('-year')
    
    # Если годов нет, ставим текущий
    current_year = timezone.now().year
    if not available_years:
        available_years = [current_year]
    
    # Выбранный год
    selected_year = request.GET.get('year')
    try:
        selected_year = int(selected_year)
    except (ValueError, TypeError):
        selected_year = available_years[0] if available_years else current_year
        
    # Данные за выбранный год
    year_tenders = closed_tenders_qs.filter(end_time__year=selected_year)

    # Список уникальных городов из всех направлений
    available_cities = Direction.objects.values_list('city_name', flat=True).distinct().order_by('city_name')
    
    # Фильтры для статистики по городам
    selected_city = request.GET.get('city', '')
    selected_month = request.GET.get('month', '')
    try:
        if selected_month:
            selected_month = int(selected_month)
    except (ValueError, TypeError):
        selected_month = ''
    
    # Агрегация по месяцам (для таблицы)
    stats_data = []
    
    # Названия месяцев
    month_names = {
        1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
        5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
        9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
    }
    
    for month_num in range(12, 0, -1):
        month_tenders = year_tenders.filter(end_time__month=month_num)
        
        if not month_tenders.exists():
            continue
            
        tenders_count = month_tenders.count()
        month_winners = Winner.objects.filter(tender__in=month_tenders)
        winners_count = month_winners.count()
        total_amount = month_winners.aggregate(sum_price=Sum('price'))['sum_price'] or 0
        
        total_volume = 0
        for winner in month_winners.select_related('direction'):
            total_volume += winner.direction.volume
            
        stats_data.append({
            'm_name': month_names.get(month_num, str(month_num)),
            't_cnt': tenders_count,
            'w_cnt': winners_count,
            't_amt': float(total_amount),
            't_vol': total_volume,
        })
    
    # Итого за год (общие показатели)
    total_tenders_year = year_tenders.count()
    total_winners_year = Winner.objects.filter(tender__in=year_tenders).count()
    year_winners = Winner.objects.filter(tender__in=year_tenders)
    total_amount_year = year_winners.aggregate(sum_price=Sum('price'))['sum_price'] or 0
    total_volume_year = 0
    for w in year_winners.select_related('direction'):
        total_volume_year += w.direction.volume

    # Данные для графика (хронологически)
    monthly_chart_labels = [row['m_name'] for row in reversed(stats_data)]
    monthly_chart_data = [row['t_amt'] for row in reversed(stats_data)]

    context = {
        'available_years': available_years,
        'selected_year': selected_year,
        'stats_data': stats_data,
        'year_totals': {
            'tenders': total_tenders_year,
            'winners': total_winners_year,
            'amount': total_amount_year,
            'volume': total_volume_year,
        },
        'monthly_chart_labels_json': json.dumps(monthly_chart_labels),
        'monthly_chart_data_json': json.dumps(monthly_chart_data),
    }
    
    return render(request, 'core/leadership_statistics.html', context)


@leadership_required
@login_required
def leadership_city_statistics(request):
    """Статистика по конкретным городам"""
    closed_tenders_qs = Tender.objects.filter(status='closed')
    
    available_years = closed_tenders_qs.annotate(
        year=ExtractYear('end_time')
    ).values_list('year', flat=True).distinct().order_by('-year')
    
    current_year = timezone.now().year
    if not available_years:
        available_years = [current_year]
    
    selected_year = request.GET.get('year')
    try:
        selected_year = int(selected_year)
    except (ValueError, TypeError):
        selected_year = available_years[0] if available_years else current_year
        
    available_cities = Direction.objects.values_list('city_name', flat=True).distinct().order_by('city_name')
    
    selected_city = request.GET.get('city', '')
    selected_month = request.GET.get('month', '')
    try:
        if selected_month:
            selected_month = int(selected_month)
    except (ValueError, TypeError):
        selected_month = ''
    
    month_names = {
        1: 'Январь', 2: 'Февраль', 3: 'Март', 4: 'Апрель',
        5: 'Май', 6: 'Июнь', 7: 'Июль', 8: 'Август',
        9: 'Сентябрь', 10: 'Октябрь', 11: 'Ноябрь', 12: 'Декабрь'
    }
    
    city_stats = {
        'total_volume': 0,
        'total_shipments': 0,
        'total_amount': 0,
        'chart_labels': [],
        'chart_data': []
    }

    if selected_city:
        city_winners_qs = Winner.objects.filter(
            direction__city_name=selected_city,
            tender__end_time__year=selected_year,
            tender__status='closed'
        )
        
        if selected_month:
            city_winners_qs = city_winners_qs.filter(tender__end_time__month=selected_month)
        
        city_stats['total_shipments'] = city_winners_qs.count()
        city_stats['total_amount'] = city_winners_qs.aggregate(sum_price=Sum('price'))['sum_price'] or 0
        
        for w in city_winners_qs.select_related('direction', 'tender').order_by('tender__end_time'):
            city_stats['total_volume'] += w.direction.volume
            label = f"{w.tender.name} ({w.tender.end_time.strftime('%d.%m')})"
            city_stats['chart_labels'].append(label)
            city_stats['chart_data'].append(float(w.price))

    context = {
        'available_years': available_years,
        'selected_year': selected_year,
        'available_cities': available_cities,
        'selected_city': selected_city,
        'selected_month': selected_month,
        'month_names': month_names,
        'city_stats': city_stats,
        'chart_labels_json': json.dumps(city_stats['chart_labels']),
        'chart_data_json': json.dumps(city_stats['chart_data']),
    }
    
    return render(request, 'core/leadership_city_statistics.html', context)
