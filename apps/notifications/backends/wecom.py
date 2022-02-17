from django.conf import settings

from common.sdk.im.wecom import WeCom as Client
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

    def send_msg(self, users, message, subject=None):
        accounts, __, __ = self.get_accounts(users)
        return self.wecom.send_text(accounts, message, markdown=True)


backend = WeCom
