from django.conf import settings
from django.core.mail import send_mail


class Email:
    def send_msg(self, accounts, subject, message):
        from_email = settings.EMAIL_FROM or settings.EMAIL_HOST_USER
        send_mail(subject, message, from_email, accounts)
