from django.urls import path
from . import views
from . import views_leadership

urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('switch-account/', views.switch_account, name='switch_account'),
    path('dashboard/', views.manager_dashboard, name='manager_dashboard'),
    path('tender/<int:tender_id>/', views.tender_detail, name='tender_detail'),
    path('api/best-price/<int:direction_id>/', views.get_best_price, name='get_best_price'),
    path('sse/tender/<int:tender_id>/', views.sse_tender_prices, name='sse_tender_prices'),
    path('submit-bid/', views.submit_bid, name='submit_bid'),
    path('help/', views.help_page, name='help_page'),
    path('admin/tender/<int:tender_id>/close/', views.close_tender, name='close_tender'),
    path('admin/tender/<int:tender_id>/report/', views.download_tender_report, name='download_tender_report'),
    path('admin/tender/<int:tender_id>/open/', views.open_tender, name='open_tender'),
    path('admin/tender/<int:tender_id>/protocol-pdf/', views.download_tender_protocol_pdf, name='download_tender_protocol_pdf'),
    # Панель руководства
    path('leadership/', views_leadership.leadership_dashboard, name='leadership_dashboard'),
    path('leadership/tender/<int:tender_id>/', views_leadership.leadership_tender_detail, name='leadership_tender_detail'),
    path('leadership/tender/<int:tender_id>/report/', views_leadership.leadership_tender_report, name='leadership_tender_report'),
    path('leadership/tender/<int:tender_id>/matrix-report/', views_leadership.leadership_tender_matrix_report, name='leadership_tender_matrix_report'),
    path('leadership/statistics/', views_leadership.leadership_statistics, name='leadership_statistics'),
    path('leadership/statistics/cities/', views_leadership.leadership_city_statistics, name='leadership_city_statistics'),
]