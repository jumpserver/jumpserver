import importlib

from django.utils.translation import gettext_lazy as _
from django.db import models

client_name_mapper = {}


class BACKEND(models.TextChoices):
    EMAIL = 'email', _('Email')
    WECOM = 'wecom', _('WeCom')
    DINGTALK = 'dingtalk', _('DingTalk')
    SITE_MSG = 'site_msg', _('Site message')
    FEISHU = 'feishu', _('FeiShu')
    SLACK = 'slack', _('Slack')
    # SMS = 'sms', _('SMS')

    @property
    def client(self):
        return client_name_mapper[self]

    def get_account(self, user):
        return self.client.get_account(user)

    @property
    def is_enable(self):
        return self.client.is_enable()

    @classmethod
    def filter_enable_backends(cls, backends):
        enable_backends = [b for b in backends if cls(b).is_enable]
        return enable_backends


for b in BACKEND:
    m = importlib.import_module(f'.{b}', __package__)
    client_name_mapper[b] = m.backend
