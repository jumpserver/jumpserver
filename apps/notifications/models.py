from importlib import import_module

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.apps import apps
from django.db import models

from common.db.models import JMSModel
from common.fields.model import JsonListCharField
from .backends.wecom import WeCom
from .backends.email import Email
from .backends.dingtalk import DingTalk


class BACKEND(models.TextChoices):
    WECOM = 'wecom', _('WeCom')
    EMAIL = 'email', _('Email')
    DINGTALK = 'dingtalk', _('DingTalk')

    @property
    def client(self):
        client = {
            self.WECOM: WeCom,
            self.EMAIL: Email,
            self.DINGTALK: DingTalk
        }[self]
        return client

    @classmethod
    def get_backend_user_id(cls, user, backend):
        id_field = {
            cls.WECOM: 'wecom_id',
            cls.DINGTALK: 'dingtalk_id',
            cls.EMAIL: 'email'
        }[backend]

        id = getattr(user, id_field)
        return id

    @classmethod
    def is_backend_enable(cls, backend):
        config_field = {
            cls.WECOM: 'AUTH_WECOM',
            cls.DINGTALK: 'AUTH_DINGTALK',
            cls.EMAIL: 'EMAIL_HOST_USER'
        }[backend]
        enable = getattr(settings, config_field)
        return bool(enable)

    @classmethod
    def filter_enable_backends(cls, backends):
        enable_backends = [b for b in backends if cls.is_backend_enable(b)]
        return enable_backends


class UserMsgSubscription(JMSModel):
    message_type = models.CharField(max_length=128)
    user = models.ForeignKey('users.User', related_name='user_msg_subscriptions', on_delete=models.CASCADE)
    receive_backends = JsonListCharField(max_length=256)

    def __str__(self):
        return f'{self.message_type}'


class SystemMsgSubscription(JMSModel):
    message_type = models.CharField(max_length=128, unique=True)
    users = models.ManyToManyField('users.User', related_name='system_msg_subscriptions')
    groups = models.ManyToManyField('users.UserGroup', related_name='system_msg_subscriptions')
    receive_backends = JsonListCharField(max_length=256)

    message_type_label = ''

    def __str__(self):
        return f'{self.message_type}'

    def __repr__(self):
        return self.__str__()

    @property
    def receivers(self):
        users = [user for user in self.users.all()]

        for group in self.groups.all():
            for user in group.users.all():
                users.append(user)

        receive_backends = self.receive_backends
        receviers = []

        for user in users:
            recevier = {'name': str(user), 'id': user.id}
            for backend in receive_backends:
                recevier[backend] = bool(BACKEND.get_backend_user_id(user, backend))
            receviers.append(recevier)

        return receviers


class SiteMessage(JMSModel):
    subject = models.CharField(max_length=1024)
    message = models.TextField()
    users = models.ManyToManyField(
        'users.User', through='site_message.SiteMessageUsers', related_name='recv_site_messages'
    )
    groups = models.ManyToManyField('users.UserGroup')
    is_broadcast = models.BooleanField(default=False)
    sender = models.ForeignKey(
        'users.User', db_constraint=False, on_delete=models.DO_NOTHING, null=True, default=None,
        related_name='send_site_message'
    )

    has_read = False
    read_at = None


class SiteMessageUsers(JMSModel):
    sitemessage = models.ForeignKey('site_message.SiteMessage', on_delete=models.CASCADE, db_constraint=False, related_name='m2m_sitemessageusers')
    user = models.ForeignKey('users.User', on_delete=models.CASCADE, db_constraint=False, related_name='m2m_sitemessageusers')
    has_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(default=None, null=True)
