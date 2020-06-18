# coding: utf-8
# 

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils import lazyproperty
from .base import BasePermission

__all__ = [
    'DatabaseAppPermission',
]


class DatabaseAppPermission(BasePermission):
    database_apps = models.ManyToManyField(
        'applications.DatabaseApp', related_name='granted_by_permissions',
        blank=True, verbose_name=_("DatabaseApp")
    )
    system_users = models.ManyToManyField(
        'assets.SystemUser', related_name='granted_by_database_app_permissions',
        verbose_name=_("System user")
    )

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _('DatabaseApp permission')
        ordering = ('name',)

    def get_all_database_apps(self):
        return self.database_apps.all()

    @lazyproperty
    def database_apps_amount(self):
        return self.database_apps.count()

    @lazyproperty
    def system_users_amount(self):
        return self.system_users.count()
