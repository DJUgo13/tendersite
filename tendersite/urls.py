from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.http import HttpResponseNotFound

def block_admin(request):
    """Возвращает 404 для стандартных путей админки"""
    return HttpResponseNotFound()

urlpatterns = [
    # Блокировка стандартных путей
    path('admin/', block_admin),
    path('administrator/', block_admin),
    path('wp-admin/', block_admin),
    path('backend/', block_admin),
    
    # Защищенный путь к админке
    path('secure-admin-control/', admin.site.urls),
    
    path('', RedirectView.as_view(url='/core/', permanent=True)),
    path('core/', include('core.urls')),  # Все наши страницы будут по адресу /core/...
]

from django.conf import settings
from django.conf.urls.static import static

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static('/static/', document_root=settings.BASE_DIR / 'static')
