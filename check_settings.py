import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tendersite.settings")
django.setup()

from django.conf import settings

def check_settings():
    print(f"EMAIL_MODE: {settings.EMAIL_MODE}")
    print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
    print(f"CELERY_TASK_ALWAYS_EAGER: {settings.CELERY_TASK_ALWAYS_EAGER}")
    print(f"DEBUG: {settings.DEBUG}")

if __name__ == "__main__":
    check_settings()
