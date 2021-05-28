from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.db import models

from .dingtalk import DingTalk
from .email import Email
from .site_msg import SiteMessage
from .wecom import WeCom


class BACKEND(models.TextChoices):
    WECOM = 'wecom', _('WeCom')
    EMAIL = 'email', _('Email')
    DINGTALK = 'dingtalk', _('DingTalk')
    SITE_MSG = 'site_msg', _('Site message')

    @property
    def client(self):
        client = {
            self.WECOM: WeCom,
            self.EMAIL: Email,
            self.DINGTALK: DingTalk,
            self.SITE_MSG: SiteMessage
        }[self]
        return client

    @classmethod
    def get_backend_user_id(cls, user, backend):
        id_field = {
            cls.WECOM: 'wecom_id',
            cls.DINGTALK: 'dingtalk_id',
            cls.EMAIL: 'email',
            cls.SITE_MSG: 'id',
        }[backend]

        return cls(backend).client().get_backend_user_id(user)

    @classmethod
    def is_backend_enable(cls, backend):
        if backend in (cls.SITE_MSG,):
            return True

        config_field = {
            cls.WECOM: 'AUTH_WECOM',
            cls.DINGTALK: 'AUTH_DINGTALK',
            cls.EMAIL: 'EMAIL_HOST_USER',
        }[backend]
        enable = getattr(settings, config_field)
        return bool(enable)

    @classmethod
    def filter_enable_backends(cls, backends):
        enable_backends = [b for b in backends if cls.is_backend_enable(b)]
        return enable_backends
