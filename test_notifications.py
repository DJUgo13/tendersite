import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tendersite.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import Tender, Direction, Company, Bid
from core.views import close_tender_and_notify_winners
from django.utils import timezone

def test_notifications():
    print("Starting notification test...")
    
    # 0. Ensure an admin user exists
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.create_superuser('admin_test', 'admin@test.com', 'password')
    
    # 1. Create tender
    tender = Tender.objects.create(
        name=f"Test Tender {timezone.now().timestamp()}", 
        status='open',
        admin=admin_user
    )
    direction = Direction.objects.create(tender=tender, city_name="Test City", volume=10, start_price=1000)
    
    # 2. Get/Create test users and companies
    u1, _ = User.objects.get_or_create(username="winner_user", defaults={'email': 'winner@test.com'})
    u2, _ = User.objects.get_or_create(username="loser_user", defaults={'email': 'loser@test.com'})
    
    c1, _ = Company.objects.get_or_create(name="Winner Company", defaults={'user': u1, 'inn': '1111111111'})
    c2, _ = Company.objects.get_or_create(name="Loser Company", defaults={'user': u2, 'inn': '2222222222'})
    
    # 3. Create bids
    Bid.objects.create(tender=tender, direction=direction, company=c1, price=800)
    Bid.objects.create(tender=tender, direction=direction, company=c2, price=900)
    
    print(f"Bids created. {c1.name} (800) vs {c2.name} (900)")
    
    # 4. Close tender
    print("Closing tender...")
    results = close_tender_and_notify_winners(tender)
    
    for res in results:
        print(f"Direction {res['direction'].city_name}: Winner {res['winner'].name}, Success: {res['success']}")

    print("\nCheck Celery logs for send_winner_email_task and send_loss_email_task triggers.")

if __name__ == "__main__":
    test_notifications()
