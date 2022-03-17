# coding: utf-8
#

from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from common.utils import lazyproperty
from .base import BasePermission, Action
from applications.models import Application
from users.models import User
from applications.const import AppCategory, AppType

__all__ = [
    'ApplicationPermission',
]


class ApplicationPermission(BasePermission):
    category = models.CharField(
        max_length=16, choices=AppCategory.choices, verbose_name=_('Category')
    )
    type = models.CharField(
        max_length=16, choices=AppType.choices, verbose_name=_('Type')
    )
    applications = models.ManyToManyField(
        'applications.Application', related_name='granted_by_permissions', blank=True,
        verbose_name=_("Application")
    )
    system_users = models.ManyToManyField(
        'assets.SystemUser',
        related_name='granted_by_application_permissions', blank=True,
        verbose_name=_("System user")
    )

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _('Application permission')
        permissions = [
        ]
        ordering = ('name',)

    @property
    def category_remote_app(self):
        return self.category == AppCategory.remote_app.value

    @property
    def category_db(self):
        return self.category == AppCategory.db.value

    @property
    def category_cloud(self):
        return self.category == AppCategory.cloud.value

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
        user_ids = self.users.all().values_list('id', flat=True)
        user_group_ids = self.user_groups.all().values_list('id', flat=True)
        users = User.objects.filter(
            Q(id__in=user_ids) | Q(groups__id__in=user_group_ids)
        )
        return users

    @classmethod
    def get_include_actions_choices(cls, category=None):
        actions = {Action.ALL, Action.CONNECT}
        if category == AppCategory.db:
            _actions = [Action.UPLOAD, Action.DOWNLOAD]
        elif category == AppCategory.remote_app:
            _actions = [
                Action.UPLOAD, Action.DOWNLOAD,
                Action.CLIPBOARD_COPY, Action.CLIPBOARD_PASTE
            ]
        else:
            _actions = []
        actions.update(_actions)

        if (Action.UPLOAD in actions) or (Action.DOWNLOAD in actions):
            actions.update([Action.UPDOWNLOAD])
        if (Action.CLIPBOARD_COPY in actions) or (Action.CLIPBOARD_PASTE in actions):
            actions.update([Action.CLIPBOARD_COPY_PASTE])

        choices = [Action.NAME_MAP[action] for action in actions]
        return choices

    @classmethod
    def get_exclude_actions_choices(cls, category=None):
        include_choices = cls.get_include_actions_choices(category)
        exclude_choices = set(Action.NAME_MAP.values()) - set(include_choices)
        return exclude_choices


class PermedApplication(Application):
    class Meta:
        proxy = True
        verbose_name = _('Permed application')
        default_permissions = []
        permissions = [
            ('view_myapps', _('Can view my apps')),
            ('view_userapps', _('Can view user apps')),
            ('view_usergroupapps', _('Can view usergroup apps')),
        ]
