from django.conf import settings

from common.message.backends.wecom import WeCom as Client
from ..base import BackendBase


class WeCom(BackendBase):
    def __init__(self):
        self.wecom = Client(
            corpid=settings.WECOM_CORPID,
            corpsecret=settings.WECOM_CORPSECRET,
            agentid=settings.WECOM_AGENTID
        )

    def send_msg(self, users, msg):
        accounts, __, __ = self.get_accounts_on_model_fields(users, 'wecom_id')
        return self.wecom.send_text(accounts, msg)
