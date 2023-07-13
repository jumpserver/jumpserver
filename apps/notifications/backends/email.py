from django.conf import settings
from django.core.mail import send_mail

from .base import BackendBase


class Email(BackendBase):
    account_field = 'email'
    is_enable_field_in_settings = 'EMAIL_HOST_USER'

    def send_msg(self, users, message, subject):
        from_email = settings.EMAIL_FROM or settings.EMAIL_HOST_USER
        accounts, __, __ = self.get_accounts(users)
        subject = (settings.EMAIL_SUBJECT_PREFIX or '') + subject
        send_mail(subject, message, from_email, accounts, html_message=message)


backend = Email
