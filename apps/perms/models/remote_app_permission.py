#  coding: utf-8
#

from django.db import models
from django.utils.translation import ugettext_lazy as _

from .base import BasePermission

__all__ = [
    'RemoteAppPermission',
]


class RemoteAppPermission(BasePermission):
    remote_apps = models.ManyToManyField('applications.RemoteApp', related_name='granted_by_permissions', blank=True, verbose_name=_("RemoteApp"))

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _('RemoteApp permission')
        ordering = ('name',)

    def get_all_remote_apps(self):
        return set(self.remote_apps.all())
