from django.conf import settings

from common.message.backends.dingtalk import DingTalk as Client
from ..base import BackendBase


class DingTalk(BackendBase):
    def __init__(self):
        self.dingtalk = Client(
            appid=settings.DINGTALK_APPKEY,
            appsecret=settings.DINGTALK_APPSECRET,
            agentid=settings.DINGTALK_AGENTID
        )

    def send_msg(self, users, msg):
        accounts, __, __ = self.get_accounts_on_model_fields(users, 'dingtalk_id')
        return self.dingtalk.send_text(accounts, msg)
