from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils.html import format_html
from .models import Reservation
from datetime import datetime
from twilio.rest import Client
from AIvapi.models import Assistance
from twilio.base.exceptions import TwilioRestException



def send_twilio_sms_via_assistance(restaurant, body, to_phone):
    """
    Send SMS using Twilio credentials stored in Assistance model for a restaurant.
    """
    try:
        assistance = restaurant.ai_assistance
    except Assistance.DoesNotExist:
        return None

    account_sid = assistance.twilio_account_sid
    auth_token = assistance.twilio_auth_token
    from_phone = assistance.twilio_number

    if not all([account_sid, auth_token, from_phone, to_phone]):
        return None

    client = Client(account_sid, auth_token)
    try:
        message = client.messages.create(
            body=body,
            from_=from_phone,
            to=to_phone
        )
        return message.sid
    except TwilioRestException as e:
        print(f"Twilio Error: {e}")
        return None



def send_reservation_verified_email(reservation):
    """Send a verification email when user already has an unfinished reservation."""
    if not reservation.customer or not reservation.customer.email:
        return
    
    customer_name = reservation.customer.customer_name
    customer_email = reservation.customer.email
    
    verify_link = f"https://api.trusttaste.ai/public/reservations/verify/{reservation.id}/"

    subject = f"🔔 Verify Your Reservation (ID: {reservation.id})"
    message = format_html(f"""
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reservation Verification</title>
    </head>
    <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 0; color: #333;">
        <div style="width: 100%; max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
            
            <div style="text-align: center; margin-bottom: 20px;">
                <h3 style="font-size: 24px; color: #007bff; margin: 0;">Hello {customer_name},</h3>
            </div>

            <div style="font-size: 16px; line-height: 1.6; color: #555; margin-bottom: 20px;">
                <p>We noticed that you already have an ongoing reservation. To ensure everything is in order, please verify your new reservation.</p>
                <p>Please verify your reservation by clicking the link below:</p>
            </div>

            <div style="text-align: center; margin-bottom: 20px;">
                <a href="{verify_link}" style="background-color: #007bff; color: white; padding: 12px 18px; font-size: 16px; border-radius: 5px; text-decoration: none; display: inline-block;">
                    Verify Reservation
                </a>
            </div>

            <div style="font-size: 16px; line-height: 1.6; color: #555; margin-bottom: 20px;">
                <p>Or copy this link to your browser:</p>
                <p><a href="{verify_link}" style="color: #007bff; text-decoration: none;">{verify_link}</a></p>
            </div>

            <div style="font-size: 14px; color: #777; text-align: center;">
                <p>Thank you for choosing us!</p>
            </div>

        </div>
    </body>
    </html>
""")


    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [customer_email],
        html_message=message
    )



def send_reservation_confirmation_email_manual(reservation):
    """Send reservation confirmation email (can be used in signals or manually)."""
    if not reservation.customer or not reservation.customer.email:
        return
    

    customer = reservation.customer
    table = reservation.table
    restaurant = table.restaurant

    customer_name = customer.customer_name
    customer_email = customer.email
    customer_phone = customer.phone
    customer_guest_no = reservation.guest_no
    customer_from_time = reservation.from_time.strftime('%I:%M %p')
    customer_to_time = reservation.to_time.strftime('%I:%M %p')

    restaurant_email = restaurant.owner.email if restaurant.owner else None
    restaurant_phone1 = restaurant.phone_number_1
    restaurant_phone2 = restaurant.twilio_number
    website = getattr(restaurant, "website", "")
    restaurant_address = restaurant.address


    subject = "Reservation Confirmation"
    message = format_html(
        """
        <h3>Your reservation is confirmed!</h3>
        <p>Thank you for making a reservation with <b>{restaurant_name}</b>.</p>
        <p><b>Reservation Details:</b></p>
        <ul>
            <li><b>Name:</b> {customer_name}</li>
            <li><b>Phone:</b> {customer_phone}</li>
            <li><b>Email:</b> {customer_email}</li>
            <li><b>Date:</b> {reservation_date}</li>
            <li><b>Start Time:</b> {customer_from_time}</li>
            <li><b>End Time:</b> {customer_to_time}</li>
            <li><b>Guests:</b> {customer_guest_no}</li>
            <li><b>Table:</b> {table_name}</li>
        </ul>
        <p><b>Restaurant Details:</b></p>
        <ul>
            <li><b>Email:</b> {restaurant_email}</li>
            <li><b>Phone:</b> {restaurant_phone1}</li>
            <li><b>Phone Online:</b> {restaurant_phone2}</li>
            <li><b>Address:</b> {restaurant_address}</li>
            <li><b>Website:</b> {website}</li>
        </ul>
        <p>We look forward to welcoming you!</p>
        <p>For any inquiries, feel free to contact us.</p>
        """,
        restaurant_name=restaurant.resturent_name,
        reservation_date=reservation.date,
        customer_from_time=customer_from_time,
        customer_to_time=customer_to_time,
        table_name=table.table_name,
        restaurant_email=restaurant_email,
        restaurant_phone1=restaurant_phone1,
        restaurant_phone2=restaurant_phone2,
        website=website,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_guest_no=customer_guest_no,
        customer_email=customer_email,
        restaurant_address=restaurant_address,
    )

    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [customer_email],
        html_message=message
    )



@receiver(post_save, sender=Reservation)
def send_reservation_confirmation_email(sender, instance, created, **kwargs):
    """
    Signal to send reservation confirmation when reservation is first created.
    """
    reservation = instance

    # Check if this customer already has unfinished reservations
    if reservation.customer and reservation.customer.phone:
        unfinished_reservations = Reservation.objects.filter(
            customer__phone=reservation.customer.phone
        ).exclude(status='finished')
        if not unfinished_reservations.exclude(id=reservation.id).exists():
            send_reservation_verified_email(reservation)
            return

    if created:
        send_reservation_confirmation_email_manual(reservation)




# @receiver(post_save, sender=Reservation)
# def send_reservation_confirmation_email(sender, instance, created, **kwargs):

#     """Send confirmation email when a new reservation is created"""

#     if created:
#         reservation = instance
#         table = reservation.table
#         restaurant = table.restaurant

#         customer_email = reservation.email
#         if not customer_email:
#             return
        
#         if reservation.phone_number:
#             unfinished_reservations = Reservation.objects.filter(
#             phone_number=reservation.phone_number
#         ).exclude(status='finished')
#             print(unfinished_reservations)
#             if unfinished_reservations.exclude(id=reservation.id).exists():
#                 send_reservation_verified_email(reservation)
#                 return
        
#         customer_name = reservation.customer_name
#         customer_phone = reservation.phone_number
#         customer_from_time = reservation.from_time.strftime('%I:%M %p')
#         customer_to_time = reservation.to_time.strftime('%I:%M %p')
#         customer_guest_no = reservation.guest_no

#         restaurant_email = restaurant.owner.email if restaurant.owner else None
#         restaurant_phone1 = restaurant.phone_number_1
#         restaurant_phone2 = restaurant.twilio_number
#         website = getattr(restaurant, "website", "")
#         restaurant_address = restaurant.address
#         opening_time = restaurant.opening_time.strftime('%H:%M') if restaurant.opening_time else "Not Set"
#         closing_time = restaurant.closing_time.strftime('%H:%M') if restaurant.closing_time else "Not Set"

#         subject = "Reservation Confirmation"
#         message = format_html(
#             """
#             <h3>Your reservation is confirmed!</h3>
#             <p>Thank you for making a reservation with <b>{restaurant_name}</b>.</p>
#             <p><b>Reservation Details:</b></p>
#             <ul>
#                 <li><b>Name:</b> {customer_name}</li>
#                 <li><b>Phone:</b> {customer_phone}</li>
#                 <li><b>Email:</b> {customer_email}</li>
#                 <li><b>Date:</b> {reservation_date}</li>
#                 <li><b>Start Time:</b> {customer_from_time}</li>
#                 <li><b>End Time:</b> {customer_to_time}</li>
#                 <li><b>Guests:</b> {customer_guest_no}</li>
#                 <li><b>Table:</b> {table_name}</li>
#             </ul>
#             <p><b>Restaurant Details:</b></p>
#             <ul>
#                 <li><b>Email:</b> {restaurant_email}</li>
#                 <li><b>Phone:</b> {restaurant_phone1}</li>
#                 <li><b>Phone Online:</b> {restaurant_phone2}</li>
#                 <li><b>Address:</b> {restaurant_address}</li>
#                 <li><b>Website:</b> {website}</li>
#                 <li><b>Opening Time:</b> {opening_time}</li>
#                 <li><b>Closing Time:</b> {closing_time}</li>
#             </ul>
#             <p>We look forward to welcoming you!</p>
#             <p>For any inquiries, feel free to contact us.</p>
#             """,
#             restaurant_name=restaurant.resturent_name,
#             reservation_date=reservation.date,
#             customer_from_time=customer_from_time,
#             customer_to_time=customer_to_time,
#             table_name=table.table_name,
#             restaurant_email=restaurant_email,
#             restaurant_phone1=restaurant_phone1,
#             restaurant_phone2=restaurant_phone2,
#             website=website,
#             opening_time=opening_time,
#             closing_time=closing_time,
#             customer_name=customer_name,
#             customer_phone=customer_phone,
#             customer_guest_no=customer_guest_no,
#             customer_email=customer_email,
#             restaurant_address=restaurant_address,
#         )

#         if reservation.email:
#             send_mail(
#                 subject,
#                 message,
#                 settings.EMAIL_HOST_USER,
#                 [customer_email],
#                 html_message=message
#             )


#         # if reservation.phone_number:
#         #     sms_text = (
#         #     f"Hi {reservation.customer_name}, your reservation at {restaurant.resturent_name} "
#         #     f"on {reservation.date} from {reservation.from_time.strftime('%I:%M %p')} "
#         #     f"to {reservation.to_time.strftime('%I:%M %p')} for {reservation.guest_no} guest(s) is confirmed."
#         # )
#         # send_twilio_sms_via_assistance(restaurant, sms_text, reservation.phone_number)








from datetime import datetime, timedelta
from django.utils import timezone
from .tasks import send_reservation_reminder_email, send_reservation_reminder_sms


@receiver(post_save, sender=Reservation)
def schedule_reservation_reminder(sender, instance, created, **kwargs):
    """Schedule reminder 30 minutes before reservation starts"""
    if created and instance.customer:
        reservation_datetime = datetime.combine(instance.date, instance.from_time)
        reservation_datetime = timezone.make_aware(reservation_datetime, timezone.get_current_timezone())

        reminder_time = reservation_datetime - timedelta(minutes=30)

        if reminder_time > timezone.now():
            subject = "Reservation Reminder"
            message = f"""
                Hi {instance.customer.customer_name},

                This is a reminder that your reservation at {instance.table.restaurant.resturent_name}
                is scheduled for {reservation_datetime.strftime('%Y-%m-%d %I:%M %p')}.
                We look forward to seeing you!
            """

            if instance.customer.email:
                send_reservation_reminder_email.apply_async(
                    args=[instance.customer.email, subject, message],
                    eta=reminder_time
                )

            # if instance.customer.phone:
            #     sms_text = (
            #         f"Reminder: Hi {instance.customer_name}, your reservation at "
            #         f"{instance.table.restaurant.resturent_name} starts at "
            #         f"{reservation_datetime.strftime('%I:%M %p')} today."
            #     )
            #     send_reservation_reminder_sms.apply_async(
            #         args=[instance.table.restaurant.id, sms_text, instance.phone_number],
            #         eta=reminder_time
                # )



