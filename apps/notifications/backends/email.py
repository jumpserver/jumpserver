from common.tasks import send_mail_async
from .base import BackendBase


class Email(BackendBase):
    account_field = 'email'
    is_enable_field_in_settings = 'EMAIL_HOST_USER'

    def send_msg(self, users, message, subject):
        accounts, __, __ = self.get_accounts(users)
        send_mail_async(subject, message, accounts, html_message=message)


backend = Email
