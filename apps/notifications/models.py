from importlib import import_module

from django.utils.translation import gettext_lazy as _
from django.apps import apps
from django.db import models

from .backends.wecom import WeCom
from .backends.email import Email
from orgs.mixins.models import OrgModelMixin


class Backend(models.Model):
    class BACKEND(models.TextChoices):
        WECOM = 'wecom', _('WeCom')
        EMAIL = 'email', _('Email')

        @property
        def client(self):
            client = {
                self.WECOM: WeCom,
                self.EMAIL: Email
            }[self]
            return client

    name = models.CharField(max_length=64, choices=BACKEND.choices, default='', db_index=True)


class Message(models.Model):
    app = models.CharField(max_length=64, default='', db_index=True)
    message = models.CharField(max_length=128, default='', db_index=True)

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


class Subscription(models.Model):
    users = models.ManyToManyField('users.User', related_name='subscriptions')
    groups = models.ManyToManyField('users.UserGroup', related_name='subscriptions')
    messages = models.ManyToManyField(Message, related_name='subscriptions')
    receive_backends = models.ManyToManyField(Backend, related_name='subscriptions')
