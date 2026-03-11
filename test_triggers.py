import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tendersite.settings")
django.setup()

from core.models import Tender, Winner, Direction, Bid
from core.utils import send_tender_started_emails, send_winner_email

def test_triggers():
    print("--- Testing Start Email Trigger ---")
    tender = Tender.objects.first()
    if tender:
        print(f"Testing for Tender ID: {tender.id}")
        res = send_tender_started_emails(tender)
        print(f"Result: {res}")
    else:
        print("No tender found.")

    print("\n--- Testing Winner Email Trigger ---")
    winner = Winner.objects.last()
    if winner:
        print(f"Testing for Winner record in Tender {winner.tender.id}")
        # Need a bid object
        bid = Bid.objects.filter(tender=winner.tender, direction=winner.direction, company=winner.company).first()
        if bid:
            success, message = send_winner_email(winner.tender, winner.direction, bid)
            print(f"Success: {success}, Message: {message}")
        else:
            print("No matching bid found for winner.")
    else:
        print("No winner record found.")

if __name__ == "__main__":
    test_triggers()
