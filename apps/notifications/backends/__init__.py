from django.utils.translation import gettext_lazy as _
from django.db import models

from .dingtalk import DingTalk
from .email import Email
from .site_msg import SiteMessage
from .wecom import WeCom


class BACKEND(models.TextChoices):
    EMAIL = 'email', _('Email')
    WECOM = 'wecom', _('WeCom')
    DINGTALK = 'dingtalk', _('DingTalk')
    SITE_MSG = 'site_msg', _('Site message')

    @property
    def client(self):
        client = {
            self.EMAIL: Email,
            self.WECOM: WeCom,
            self.DINGTALK: DingTalk,
            self.SITE_MSG: SiteMessage
        }[self]
        return client

    def get_account(self, user):
        return self.client.get_account(user)

    @property
    def is_enable(self):
        return self.client.is_enable()

    @classmethod
    def filter_enable_backends(cls, backends):
        enable_backends = [b for b in backends if cls(b).is_enable]
        return enable_backends
