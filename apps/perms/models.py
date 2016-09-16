from __future__ import unicode_literals, absolute_import
import functools

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from users.models import User, UserGroup
from assets.models import Asset, AssetGroup, SystemUser
from common.utils import date_expired_default, combine_seq


class AssetPermission(models.Model):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    users = models.ManyToManyField(User, related_name='asset_permissions', blank=True)
    user_groups = models.ManyToManyField(UserGroup, related_name='asset_permissions', blank=True)
    assets = models.ManyToManyField(Asset, related_name='granted_by_permissions', blank=True)
    asset_groups = models.ManyToManyField(AssetGroup, related_name='granted_by_permissions', blank=True)
    system_users = models.ManyToManyField(SystemUser, related_name='granted_by_permissions')
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    date_expired = models.DateTimeField(default=date_expired_default, verbose_name=_('Date expired'))
    created_by = models.CharField(max_length=128, blank=True, verbose_name=_('Created by'))
    date_created = models.DateTimeField(auto_now=True, verbose_name=_('Date created'))
    comment = models.TextField(verbose_name=_('Comment'), blank=True)

    def __unicode__(self):
        return '%(name)s: %(action)s' % {'name': self.name, 'action': self.action}

    @property
    def is_valid(self):
        if self.date_expired < timezone.now() and self.is_active:
            return True
        return True

    @staticmethod
    def set_inherited(obj, inherited_from=None):
        setattr(obj, 'inherited', True)
        setattr(obj, 'inherited_from', inherited_from)
        return obj

    @staticmethod
    def set_non_inherited(obj):
        setattr(obj, 'inherited', False)
        return obj

    def get_granted_users(self):
        users_granted_direct = map(self.set_non_inherited, self.users.all())
        return list(set(users_granted_direct) | self.get_granted_user_groups_member())

    def get_granted_user_groups_member(self):
        users = set()
        for user_group in self.user_groups.all():
            for user in user_group.users.all():
                user = self.set_inherited(user, inherited_from=user_group)
                users.add(user)
        return users

    def get_granted_assets(self):
        assets_granted_direct = map(self.set_non_inherited, self.assets.all())
        return list(set(assets_granted_direct or []) | self.get_granted_asset_groups_member())

    def get_granted_asset_groups_member(self):
        assets = set()
        for asset_group in self.asset_groups.all():
            for asset in asset_group.assets.all():
                asset = self.set_inherited(asset, inherited_from=asset_group)
                assets.add(asset)
        return assets

    class Meta:
        db_table = 'asset_permission'

