from django.conf import settings

from common.message.backends.wecom import WeCom as Client
from .base import BackendBase


class WeCom(BackendBase):
    account_field = 'wecom_id'
    is_enable_field_in_settings = 'AUTH_WECOM'

    def __init__(self):
        self.wecom = Client(
            corpid=settings.WECOM_CORPID,
            corpsecret=settings.WECOM_SECRET,
            agentid=settings.WECOM_AGENTID
        )

    def send_msg(self, users, msg):
        accounts, __, __ = self.get_accounts(users)
        return self.wecom.send_text(accounts, msg)
