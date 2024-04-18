from django.conf import settings

from common.sdk.im.lark import Lark as Client
from .base import BackendBase


class Lark(BackendBase):
    account_field = 'lark_id'
    is_enable_field_in_settings = 'AUTH_LARK'

    def __init__(self):
        self.client = Client(
            app_id=settings.LARK_APP_ID,
            app_secret=settings.LARK_APP_SECRET
        )

    def send_msg(self, users, message, subject=None):
        accounts, __, __ = self.get_accounts(users)
        print('lark', message)
        return self.client.send_text(accounts, message)


backend = Lark
