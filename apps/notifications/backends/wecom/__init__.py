from django.conf import settings

from common.message.backends.wecom import WeCom as Client


class WeCom:
    def __init__(self):
        self.wecom = Client(
            corpid=settings.WECOM_CORPID,
            corpsecret=settings.WECOM_CORPSECRET,
            agentid=settings.WECOM_AGENTID
        )

    def send_msg(self, users, msg):
        return self.wecom.send_text(users, msg)
