from django.db import models

from orgs.mixins.models import OrgModelMixin


class Backend(OrgModelMixin, models.Model):
    name = models.CharField(max_length=64, default='', db_index=True)


class Message(OrgModelMixin, models.Model):
    app_name = models.CharField(max_length=64, default='', db_index=True)
    message = models.CharField(max_length=128, default='', db_index=True)
    message_label = models.CharField(max_length=128, default='')


class Subscription(OrgModelMixin, models.Model):
    users = models.ManyToManyField('users.User', related_name='subscriptions')
    groups = models.ManyToManyField('users.UserGroup', related_name='subscriptions')
    messages = models.ManyToManyField(Message, related_name='subscriptions')
    receive_backends = models.ManyToManyField(Backend, related_name='subscriptions')
