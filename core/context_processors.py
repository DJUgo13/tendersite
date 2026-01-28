from .utils import get_user_role


def user_context(request):
    """
    Безопасные переменные для шаблонов:
    - user_company: Company или None (чтобы не падать на leadership аккаунтах)
    - user_role: 'admin' | 'manager' | 'leadership' | None
    """
    company = None
    role = None

    if hasattr(request, "user") and request.user.is_authenticated:
        role = get_user_role(request.user)
        try:
            company = request.user.company
        except Exception:
            company = None

    return {
        "user_company": company,
        "user_role": role,
    }

