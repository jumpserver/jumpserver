from django.conf import settings

from common.sdk.sms.alibaba import AlibabaSMS as Client
from .base import BackendBase


class SMS(BackendBase):
    account_field = 'phone'
    is_enable_field_in_settings = 'SMS_ENABLED'

    def __init__(self):
        """
        暂时只对接阿里，之后再扩展
        """
        self.client = Client(
            access_key_id=settings.ALIBABA_ACCESS_KEY_ID,
            access_key_secret=settings.ALIBABA_ACCESS_KEY_SECRET
        )

    def send_msg(self, users, sign_name: str, template_code: str, template_param: dict):
        accounts, __, __ = self.get_accounts(users)
        return self.client.send_sms(accounts, sign_name, template_code, template_param)


backend = SMS
