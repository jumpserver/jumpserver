#  coding: utf-8
#
from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils import lazyproperty
from .base import BasePermission

__all__ = [
    'RemoteAppPermission',
]


class RemoteAppPermission(BasePermission):
    remote_apps = models.ManyToManyField('applications.RemoteApp', related_name='granted_by_permissions', blank=True, verbose_name=_("RemoteApp"))
    system_users = models.ManyToManyField('assets.SystemUser', related_name='granted_by_remote_app_permissions', verbose_name=_("System user"))

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _('RemoteApp permission')
        ordering = ('name',)

    def get_all_remote_apps(self):
        return set(self.remote_apps.all())

    @property
    def all_remote_apps(self):
        return self.remote_apps.all()

    @lazyproperty
    def remote_apps_amount(self):
        return self.remote_apps.count()

    @lazyproperty
    def system_users_amount(self):
        return self.system_users.count()
