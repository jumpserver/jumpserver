from common.sdk.sms.endpoint import SMS
from .base import BackendBase


class SMS(BackendBase):
    account_field = 'phone'
    is_enable_field_in_settings = 'SMS_ENABLED'

    def __init__(self):
        self.client = SMS()

    def send_msg(self, users, sign_name: str, template_code: str, template_param: dict):
        accounts, __, __ = self.get_accounts(users)
        return self.client.send_sms(accounts, sign_name, template_code, template_param)


backend = SMS
