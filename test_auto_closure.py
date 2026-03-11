import os
import django
from django.utils import timezone
from datetime import timedelta

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tendersite.settings")
django.setup()

from core.models import Tender, Direction, Company, Bid
from core.utils import initialize_direction_timers, check_auto_close_directions

def test_auto_closure():
    admin_user = django.contrib.auth.models.User.objects.filter(is_staff=True).first()
    if not admin_user:
        print("No admin user found.")
        return

    print("--- 1. Creating Test Tender ---")
    tender = Tender.objects.create(
        name="Auto-Closure Test",
        admin=admin_user,
        status='draft',
        final_timer_minutes=1
    )
    d1 = Direction.objects.create(tender=tender, city_name="Test City 1", volume=1, start_price=100)
    d2 = Direction.objects.create(tender=tender, city_name="Test City 2", volume=1, start_price=200)

    print(f"Created Tender {tender.id} in status {tender.status}")

    print("\n--- 2. Opening Tender ---")
    tender.status = 'open'
    tender.save()
    initialize_direction_timers(tender)
    
    d1.refresh_from_db()
    d2.refresh_from_db()
    print(f"Direction 1 timer: {d1.final_timer_end}")
    print(f"Direction 2 timer: {d2.final_timer_end}")

    print("\n--- 3. Simulating Timer Expiration ---")
    # Expire d1 with a bid
    comp = Company.objects.first()
    if comp:
        Bid.objects.create(tender=tender, direction=d1, company=comp, price=90, created_by=admin_user)
        print("Placed bid on D1")
    
    past_time = timezone.now() - timedelta(minutes=5)
    d1.final_timer_end = past_time
    d1.save()
    d2.final_timer_end = past_time
    d2.save()
    print("Set timers to the past.")

    print("\n--- 4. Running Auto-Close Check ---")
    check_auto_close_directions()
    
    tender.refresh_from_db()
    d1.refresh_from_db()
    d2.refresh_from_db()
    
    print(f"Tender Status: {tender.status}")
    print(f"Direction 1 Winner: {d1.winner}")
    print(f"Direction 2 Winner: {d2.winner}")

    if tender.status == 'closed':
        print("\nSUCCESS: Tender automatically closed!")
    else:
        print("\nFAILURE: Tender still open.")

if __name__ == "__main__":
    test_auto_closure()
