from django.conf import settings
from twilio.rest import Client
import random
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from email.utils import formataddr
from django.utils import timezone
from datetime import timedelta
from django.db import transaction

def get_twilio_client() -> Client:
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)




def send_otp(user):
    otp = str(random.randint(100000, 999999))
    user.otp = otp
    user.otp_expired = timezone.now() + timedelta(minutes=10)

    try:
        with transaction.atomic():
            user.save()

            # Send OTP email
            subject = 'OTP Verification Request'
            from_email = formataddr(("TradLogistics", settings.EMAIL_HOST_USER))
            to = user.email
            html_content = render_to_string('otp_verification.html', {'otp': otp})
            text_content = strip_tags(html_content)
            msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
            msg.attach_alternative(html_content, "text/html")
            msg.send()
        return True, otp
    except Exception as e:
        return False, otp