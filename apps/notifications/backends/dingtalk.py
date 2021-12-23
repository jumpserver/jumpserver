from django.conf import settings
from common.sdk.im.dingtalk import DingTalk as Client
from .base import BackendBase


class DingTalk(BackendBase):
    account_field = 'dingtalk_id'
    is_enable_field_in_settings = 'AUTH_DINGTALK'

    def __init__(self):
        self.dingtalk = Client(
            appid=settings.DINGTALK_APPKEY,
            appsecret=settings.DINGTALK_APPSECRET,
            agentid=settings.DINGTALK_AGENTID
        )

    def send_msg(self, users, message, subject=None):
        accounts, __, __ = self.get_accounts(users)
        return self.dingtalk.send_markdown(accounts, subject, message)


backend = DingTalk
