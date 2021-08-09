from django.conf import settings
from django.core.mail import send_mail

from ..base import BackendBase


class Email(BackendBase):
    def send_msg(self, users, subject, message):
        from_email = settings.EMAIL_FROM or settings.EMAIL_HOST_USER
        accounts, __, __ = self.get_accounts_on_model_fields(users, 'email')
        send_mail(subject, message, from_email, accounts)
