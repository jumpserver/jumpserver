import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

import common.db.models
from common.utils.random import random_string


def default_secret():
    return random_string(36)


def default_ip_group():
    return ["*"]


class AccessKey(models.Model):
    id = models.UUIDField(verbose_name='AccessKeyID', primary_key=True, default=uuid.uuid4, editable=False)
    secret = models.CharField(verbose_name='AccessKeySecret', default=default_secret, max_length=36)
    ip_group = models.JSONField(default=default_ip_group, verbose_name=_('IP group'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='User',
                             on_delete=common.db.models.CASCADE_SIGNAL_SKIP, related_name='access_keys')
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    date_last_used = models.DateTimeField(null=True, blank=True, verbose_name=_('Date last used'))
    date_created = models.DateTimeField(auto_now_add=True)

    def get_id(self):
        return str(self.id)

    def get_secret(self):
        return str(self.secret)

    def get_full_value(self):
        return '{}:{}'.format(self.id, self.secret)

    def __str__(self):
        return str(self.id)

    class Meta:
        verbose_name = _("Access key")
