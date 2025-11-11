from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from twilio.rest import Client
from AIvapi.models import Assistance


@shared_task
def send_reservation_reminder_email(email, subject, message):
    """Send reminder email"""
    send_mail(
        subject,
        message,
        settings.EMAIL_HOST_USER,
        [email],
        html_message=message
    )
    return f"Reminder email sent to {email}"


@shared_task
def send_reservation_reminder_sms(restaurant_id, body, to_phone):
    """Send reminder SMS using Twilio assistance"""
    from restaurants.models import Restaurant
    try:
        restaurant = Restaurant.objects.get(id=restaurant_id)
        assistance = restaurant.ai_assistance
    except Exception:
        return None

    if not all([assistance.twilio_account_sid, assistance.twilio_auth_token, assistance.twilio_number, to_phone]):
        return None

    client = Client(assistance.twilio_account_sid, assistance.twilio_auth_token)
    try:
        msg = client.messages.create(
            body=body,
            from_=assistance.twilio_number,
            to=to_phone
        )
        return msg.sid
    except Exception as e:
        return str(e)
