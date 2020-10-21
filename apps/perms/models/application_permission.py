# coding: utf-8
#

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils import lazyproperty
from .base import BasePermission

__all__ = [
    'ApplicationPermission',
]


class ApplicationPermission(BasePermission):
    applications = models.ManyToManyField('applications.Application', related_name='granted_by_permissions', blank=True, verbose_name=_("Application"))
    system_users = models.ManyToManyField('assets.SystemUser', related_name='granted_by_application_permissions', verbose_name=_("System user"))

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _('Application permission')
        ordering = ('name',)

    @lazyproperty
    def users_amount(self):
        return self.users.count()

    @lazyproperty
    def user_groups_amount(self):
        return self.user_groups.count()

    @lazyproperty
    def applications_amount(self):
        return self.applications.count()

    @lazyproperty
    def system_users_amount(self):
        return self.system_users.count()
