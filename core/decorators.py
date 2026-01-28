"""
Декораторы для проверки прав доступа по ролям
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from .utils import is_admin, is_manager, is_leadership


def admin_required(view_func):
    """Декоратор для проверки прав администратора"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Требуется авторизация.')
            return redirect('login')
        
        if not is_admin(request.user):
            messages.error(request, 'Доступ запрещён. Требуются права администратора.')
            return redirect('manager_dashboard')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def manager_required(view_func):
    """Декоратор для проверки прав менеджера"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Требуется авторизация.')
            return redirect('login')
        
        if not (is_manager(request.user) or is_admin(request.user)):
            messages.error(request, 'Доступ запрещён. Требуются права менеджера.')
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def leadership_required(view_func):
    """Декоратор для проверки прав руководства"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Требуется авторизация.')
            return redirect('login')
        
        if not (is_leadership(request.user) or is_admin(request.user)):
            messages.error(request, 'Доступ запрещён. Требуются права руководства.')
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def role_required(*allowed_roles):
    """Декоратор для проверки конкретных ролей"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'Требуется авторизация.')
                return redirect('login')
            
            from .utils import get_user_role
            user_role = get_user_role(request.user)
            
            if user_role not in allowed_roles:
                messages.error(request, 'Доступ запрещён.')
                return redirect('login')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
