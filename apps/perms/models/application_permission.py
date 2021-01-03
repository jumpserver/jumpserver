# coding: utf-8
#

from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from common.utils import lazyproperty
from .base import BasePermission
from users.models import User
from applications.const import ApplicationCategoryChoices, ApplicationTypeChoices

__all__ = [
    'ApplicationPermission',
]


class ApplicationPermission(BasePermission):
    category = models.CharField(
        max_length=16, choices=ApplicationCategoryChoices.choices, verbose_name=_('Category')
    )
    type = models.CharField(
        max_length=16, choices=ApplicationTypeChoices.choices, verbose_name=_('Type')
    )
    applications = models.ManyToManyField(
        'applications.Application', related_name='granted_by_permissions', blank=True,
        verbose_name=_("Application")
    )
    system_users = models.ManyToManyField(
        'assets.SystemUser', related_name='granted_by_application_permissions',
        verbose_name=_("System user")
    )

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _('Application permission')
        ordering = ('name',)

    @property
    def category_remote_app(self):
        return self.category == ApplicationCategoryChoices.remote_app.value

    @property
    def category_db(self):
        return self.category == ApplicationCategoryChoices.db.value

    @property
    def category_cloud(self):
        return self.category == ApplicationCategoryChoices.cloud.value

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

    def get_all_users(self):
        users_id = self.users.all().values_list('id', flat=True)
        user_groups_id = self.user_groups.all().values_list('id', flat=True)
        users = User.objects.filter(
            Q(id__in=users_id) | Q(groups__id__in=user_groups_id)
        )
        return users
