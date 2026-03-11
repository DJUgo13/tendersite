from __future__ import annotations

import logging
from urllib.parse import urljoin

from celery import shared_task
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.urls import reverse

from .models import Tender, Direction, Bid, Company

logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_winner_email_task(self, tender_id: int, direction_id: int, bid_id: int) -> bool:

    try:
        tender = Tender.objects.get(id=tender_id)
        direction = Direction.objects.get(id=direction_id)
        winning_bid = Bid.objects.get(id=bid_id)
    except (Tender.DoesNotExist, Direction.DoesNotExist, Bid.DoesNotExist):
        logger.warning(f"Could not find objects for winner email: Tender {tender_id}, Direction {direction_id}, Bid {bid_id}. Task cancelled.")
        return False
    
    try:
        user_email = winning_bid.company.user.email
        if not user_email:
            logger.warning(f"No email for company {winning_bid.company.name} (winner of Tender {tender_id})")
            return False
            
        subject = f'{settings.EMAIL_SUBJECT_PREFIX}Победа в тендере "{tender.name}"'
        
        # Ссылка на тендер
        tender_url = urljoin(settings.SITE_URL, reverse("tender_detail", kwargs={"tender_id": tender.id}).lstrip("/"))

        text_message = f'''Поздравляем! Ваша компания "{winning_bid.company.name}" победила в тендере "{tender.name}".

Детали победы:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Тендер: {tender.name}
Направление: {direction.city_name}
Ваша выигрышная ставка: {winning_bid.price:,.2f} руб.
Объём: {direction.volume} машин
Дата закрытия тендера: {tender.end_time.strftime("%d.%m.%Y %H:%M") if tender.end_time else "Завершён"}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ссылка: {tender_url}

С вами свяжутся в ближайшее время для уточнения деталей и оформления договора.

С уважением,
Команда тендерной площадки'''
        
        html_message = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #28a745; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
                .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
                .details {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #28a745; }}
                .detail-row {{ margin: 10px 0; }}
                .detail-label {{ font-weight: bold; color: #555; }}
                .detail-value {{ color: #28a745; font-size: 1.1em; }}
                .footer {{ text-align: center; padding: 20px; color: #666; font-size: 0.9em; }}
                .price {{ font-size: 1.3em; font-weight: bold; color: #28a745; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1> Поздравляем с победой!</h1>
                </div>
                <div class="content">
                    <p>Ваша компания <strong>"{winning_bid.company.name}"</strong> победила в тендере <strong>"{tender.name}"</strong>!</p>
                    
                    <div class="details">
                        <div class="detail-row">
                            <span class="detail-label">Тендер:</span>
                            <span class="detail-value">{tender.name}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Направление:</span>
                            <span class="detail-value">{direction.city_name}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Ваша выигрышная ставка:</span>
                            <span class="detail-value price">{winning_bid.price:,.2f} руб.</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Объём:</span>
                            <span class="detail-value">{direction.volume} машин</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Дата закрытия тендера:</span>
                            <span class="detail-value">{tender.end_time.strftime("%d.%m.%Y %H:%M") if tender.end_time else "Завершён"}</span>
                        </div>
                    </div>
                    
                    <p style="margin: 16px 0 0 0;">
                        Ссылка на тендер:
                        <a href="{tender_url}">{tender_url}</a>
                    </p>

                    <p style="background-color: #fff3cd; padding: 15px; border-left: 4px solid #ffc107; margin-top: 20px;">
                        <strong>Важно:</strong> С вами свяжутся в ближайшее время для уточнения деталей и оформления договора.
                    </p>
                </div>
                <div class="footer">
                    <p>С уважением,<br>Команда тендерной площадки</p>
                </div>
            </div>
        </body>
        </html>
        '''
        
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user_email],
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)
        
        logger.info(f"Winner email sent to {user_email} for Tender {tender_id}")
        return True
    except Exception as e:
        logger.exception(f"Failed to send winner email for Tender {tender_id}")
        raise e


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def send_tender_started_emails_task(self, tender_id: int, site_url: str | None = None) -> dict:
    try:
        tender = Tender.objects.get(id=tender_id)
        directions_count = tender.directions.count()

        tender_path = reverse("tender_detail", kwargs={"tender_id": tender.id})
        base_url = (site_url or "").strip()
        if not base_url:
            tender_url = tender_path
        else:
            tender_url = urljoin(base_url, tender_path.lstrip("/"))

        subject = f'{settings.EMAIL_SUBJECT_PREFIX}Старт тендера "{tender.name}"'

        text_message = (
            f'Открыт тендер: {tender.name}\n'
            f'Статус: {tender.get_status_display()}\n'
            f'Количество направлений: {directions_count}\n\n'
            f'Ссылка: {tender_url}\n\n'
            f'Перейдите в систему для участия.\n'
        )

        html_message = f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="UTF-8"></head>
        <body style="font-family: Arial, sans-serif; color: #333;">
            <div style="max-width: 650px; margin: 0 auto; padding: 20px;">
                <h2 style="margin: 0 0 12px 0;">Открыт тендер: {tender.name}</h2>
                <p style="margin: 0 0 10px 0;">Статус: <strong>{tender.get_status_display()}</strong></p>
                <p style="margin: 0 0 10px 0;">Направлений: <strong>{directions_count}</strong></p>
                <p style="margin: 16px 0 0 0;">
                    Ссылка на тендер:
                    <a href="{tender_url}">{tender_url}</a>
                </p>
                <p style="margin: 16px 0 0 0;">Войдите в систему и сделайте ставку по интересующим направлениям.</p>
            </div>
        </body>
        </html>
        """.strip()

        recipients = list(
            User.objects.filter(is_active=True)
            .exclude(email__isnull=True)
            .exclude(email="")
            .values_list("email", flat=True)
            .distinct()
        )

        sent = 0
        failed = 0
        for email in recipients:
            email = (email or "").strip()
            if not email:
                continue
            try:
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=text_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[email],
                )
                msg.attach_alternative(html_message, "text/html")
                msg.send(fail_silently=False)
                sent += 1
                logger.info(f"Successfully sent start email to {email}")
            except Exception as e:
                failed += 1
                logger.error(f"Email send error to {email}: {str(e)}")

        return {"tender_id": tender.id, "queued": len(recipients), "sent": sent, "failed": failed, "tender_url": tender_url}

    except Tender.DoesNotExist:
        logger.warning(f"Tender {tender_id} not found for start emails. Task cancelled.")
        return {"error": "Tender not found"}
    except Exception as e:
        logger.exception(f"Critical error in send_tender_started_emails_task for tender {tender_id}")
        return {"error": str(e), "tender_id": tender_id}


@shared_task
def check_timers_periodic_task():
    from .utils import check_auto_close_directions
    logger.info("Running periodic timer check...")
    check_auto_close_directions()
    return "Timer check completed"

