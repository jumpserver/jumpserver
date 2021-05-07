from importlib import import_module

from django.utils.translation import gettext_lazy as _
from django.apps import apps
from django.db import models

from .backends.wecom import WeCom
from .backends.email import Email
from .backends.dingtalk import DingTalk
from orgs.mixins.models import OrgModelMixin


class Backend(models.Model):
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

    name = models.CharField(max_length=64, choices=BACKEND.choices, default='', db_index=True)


def get_backend_user_id(user, backend):
    mapper = {
        Backend.BACKEND.WECOM: 'wecom_id',
        Backend.BACKEND.DINGTALK: 'dingtalk_id',
        Backend.BACKEND.EMAIL: 'email'
    }
    id = getattr(user, mapper[backend])
    return id


class Message(models.Model):
    app = models.CharField(max_length=64, default='')
    message = models.CharField(max_length=128, unique=True)
    users = models.ManyToManyField('users.User', related_name='subscriptions')
    groups = models.ManyToManyField('users.UserGroup', related_name='subscriptions')
    receive_backends = models.ManyToManyField(Backend, related_name='subscriptions')

    def __str__(self):
        return f'{self.app} -> {self.message}'

    def __repr__(self):
        return self.__str__()

    @property
    def message_label(self):
        app_config = apps.get_app_config(self.app)
        modules = import_module('.notifications', app_config.module.__package__)
        MsgCls = getattr(modules, self.message)
        return MsgCls.message_label

    @property
    def app_label(self):
        app_config = apps.get_app_config(self.app)
        return app_config.verbose_name

    @property
    def receivers(self):
        users = [user for user in self.users.all()]

        for group in self.groups.all():
            for user in group.users.all():
                users.append(user)

        backend_names = [b.name for b in self.receive_backends.all()]
        receviers = []

        for user in users:
            recevier = {'name': str(user)}
            for backend_name in backend_names:
                recevier[backend_name] = bool(get_backend_user_id(user, backend_name))
            receviers.append(recevier)

        return receviers
