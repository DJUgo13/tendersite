import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tendersite.settings")
django.setup()

from django.conf import settings
from django.contrib.auth.models import User
from core.models import Tender, Winner, Direction, Bid

def check():
    print("--- User Check ---")
    active_users = User.objects.filter(is_active=True).exclude(email="").exclude(email__isnull=True)
    print(f"Active users with email: {active_users.count()}")
    for u in active_users:
        role = "unknown"
        try:
            role = u.profile.role
        except:
            pass
        print(f" - {u.username} ({role}): {u.email}")

    print("\n--- Tender Check ---")
    tenders = Tender.objects.all().order_by('-id')[:10]
    print(f"Total Tenders: {Tender.objects.count()}")
    for t in tenders:
        print(f" - ID: {t.id}, Name: {t.name}, Status: {t.status}, Directions: {t.directions.count()}")

    print("\n--- Recent Winners ---")
    winners = Winner.objects.all().order_by('-id')[:10]
    print(f"Total Winners records: {Winner.objects.count()}")
    for w in winners:
        print(f" - Tender: {w.tender.name} (ID: {w.tender.id}), Company: {w.company.name}, Direction: {w.direction.city_name}")

if __name__ == "__main__":
    check()
