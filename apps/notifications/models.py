from typing import List

from django.db import models

from orgs.mixins.models import OrgModelMixin


class Subscription(OrgModelMixin, models.Model):
    users = models.ManyToManyField('users.User', related_name='subscriptions')
    groups = models.ManyToManyField('users.UserGroup', related_name='subscriptions')
    app_name = models.CharField(max_length=64, default='', db_index=True)
    message = models.CharField(max_length=128, default='', db_index=True)
    receive_backends_str = models.CharField(max_length=256, default='')

    @property
    def receive_backends(self) -> List:
        backends = self.receive_backends_str.split('|')
        return backends

    @receive_backends.setter
    def receive_backends(self, backends):
        backends_str = '|'.join(backends)
        self.receive_backends_str = backends_str
