from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import Company, Tender, Direction, Bid, UserProfile
from django.urls import reverse

class ManagerWorkflowTest(TestCase):
    def setUp(self):
        # 1. Setup Data
        self.password = 'password123'
        
        # User & Company
        self.user = User.objects.create_user(username='manager', password=self.password)
        self.profile = UserProfile.objects.create(user=self.user, role='manager')
        self.company = Company.objects.create(name='TransCorp', inn='1234567890', user=self.user)
        
        # Admin
        self.admin = User.objects.create_user(username='admin', password=self.password, is_staff=True)
        
        # Tender & Direction
        self.tender = Tender.objects.create(
            name='Test Tender',
            admin=self.admin,
            status='open',
            start_time=timezone.now(),
            end_time=timezone.now() + timedelta(days=1)
        )
        self.direction = Direction.objects.create(
            tender=self.tender,
            city_name='Sochi',
            volume=5,
            start_price=Decimal('10000.00'),
            current_best_price=Decimal('10000.00')
        )
        
        # Client
        self.client = Client()
        self.client.login(username='manager', password=self.password)

    def test_manager_can_view_tender(self):
        """Test that manager can view tender details"""
        response = self.client.get(reverse('tender_detail', args=[self.tender.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Tender')
        self.assertContains(response, 'Sochi')

    def test_manager_can_place_bid(self):
        """Test placing a valid bid"""
        price = 9000.00
        response = self.client.post(reverse('submit_bid'), {
            'direction_id': self.direction.id,
            'price': price
        }, follow=True)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Bid.objects.filter(company=self.company, price=price, is_active=True).exists())
        
        # Check direction updated
        self.direction.refresh_from_db()
        self.assertEqual(self.direction.current_best_price, Decimal('9000.00'))

    def test_manager_cannot_bid_higher(self):
        """Test validation: cannot bid higher than current best"""
        response = self.client.post(reverse('submit_bid'), {
            'direction_id': self.direction.id,
            'price': 11000.00  # Higher than 10000
        }, follow=True)
        
        self.assertContains(response, 'должна быть не выше')
        self.assertFalse(Bid.objects.filter(price=11000.00).exists())

    def test_bid_history_view(self):
        """Test that bid history works and shows previous bids"""
        # Place 2 bids
        Bid.objects.create(tender=self.tender, direction=self.direction, company=self.company, price=9500, created_by=self.user, is_active=False)
        Bid.objects.create(tender=self.tender, direction=self.direction, company=self.company, price=9000, created_by=self.user, is_active=True)
        
        response = self.client.get(reverse('get_my_bid_history', args=[self.direction.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '9500')
        self.assertContains(response, '9000')

    def test_rebidding_logic_equal_price(self):
        """Test that equal price triggers rebidding state"""
        # Create another company
        other_user = User.objects.create_user(username='other', password='p')
        other_company = Company.objects.create(name='Other', inn='111', user=other_user)
        
        # Initial best bid from Other
        Bid.objects.create(
            tender=self.tender, direction=self.direction, company=other_company, 
            price=9000, created_by=other_user, is_active=True
        )
        self.direction.current_best_price = 9000
        self.direction.save()
        
        # Manager places EQUAL bid
        response = self.client.post(reverse('submit_bid'), {
            'direction_id': self.direction.id,
            'price': 9000
        }, follow=True)
        
        self.direction.refresh_from_db()
        self.assertTrue(self.direction.is_in_rebidding)
        self.assertIsNotNone(self.direction.rebidding_end_time)

    def test_final_timer_extension(self):
        """Test that new bid extends final timer"""
        initial_timer = self.direction.final_timer_end
        
        response = self.client.post(reverse('submit_bid'), {
            'direction_id': self.direction.id,
            'price': 9900
        }, follow=True)
        
        self.direction.refresh_from_db()
        self.assertIsNotNone(self.direction.final_timer_end)
        if initial_timer:
            self.assertGreater(self.direction.final_timer_end, initial_timer)
