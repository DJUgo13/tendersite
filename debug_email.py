import os
import django
from django.conf import settings
from django.core.mail import send_mail

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tendersite.settings")
django.setup()

def test_send_mail():
    print(f"Testing send_mail... EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
    try:
        sent = send_mail(
            "Test Subject",
            "Test Message",
            settings.DEFAULT_FROM_EMAIL,
            ["usnvlsnvo@mail.ru"],
            fail_silently=False,
        )
        print(f"send_mail result: {sent}")
    except Exception as e:
        print(f"send_mail failed: {e}")

def test_celery_task():
    from core.models import Tender
    from core.tasks import send_tender_started_emails_task
    
    tender = Tender.objects.first()
    if not tender:
        print("No tender found in database to test Celery task.")
        return

    print(f"Testing Celery task for tender {tender.id}...")
    try:
        # We run it synchronously (delay/apply_async) to see if it enqueues correctly
        # or call it directly to see if the logic works.
        # But here we want to see if it works as a task.
        result = send_tender_started_emails_task.apply(args=[tender.id])
        print(f"Celery task result: {result.result}")
        print(f"Celery task status: {result.status}")
    except Exception as e:
        print(f"Celery task failed: {e}")

if __name__ == "__main__":
    test_send_mail()
    print("-" * 20)
    test_celery_task()
