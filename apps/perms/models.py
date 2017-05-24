from __future__ import unicode_literals, absolute_import
import functools

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from django.db.models.signals import m2m_changed

from users.models import User, UserGroup
from assets.models import Asset, AssetGroup, SystemUser
from common.utils import date_expired_default, combine_seq


class AssetPermission(models.Model):
    # PRIVATE_FOR_CHOICE = (
    #     ('N', 'None'),
    #     ('U', 'user'),
    #     ('G', 'user group'),
    # )
    name = models.CharField(
        max_length=128, unique=True, verbose_name=_('Name'))
    users = models.ManyToManyField(
        User, related_name='asset_permissions', blank=True)
    user_groups = models.ManyToManyField(
        UserGroup, related_name='asset_permissions', blank=True)
    assets = models.ManyToManyField(
        Asset, related_name='granted_by_permissions', blank=True)
    asset_groups = models.ManyToManyField(
        AssetGroup, related_name='granted_by_permissions', blank=True)
    system_users = models.ManyToManyField(
        SystemUser, related_name='granted_by_permissions')
    is_active = models.BooleanField(
        default=True, verbose_name=_('Active'))
    date_expired = models.DateTimeField(
        default=date_expired_default, verbose_name=_('Date expired'))
    created_by = models.CharField(
        max_length=128, blank=True, verbose_name=_('Created by'))
    date_created = models.DateTimeField(
        auto_now_add=True, verbose_name=_('Date created'))
    comment = models.TextField(verbose_name=_('Comment'), blank=True)

    def __unicode__(self):
        return self.name

    @property
    def is_valid(self):
        if self.date_expired < timezone.now() and self.is_active:
            return True
        return True

    def get_granted_users(self):
        return list(set(self.users.all()) | self.get_granted_user_groups_member())

    def get_granted_user_groups_member(self):
        users = set()
        for user_group in self.user_groups.all():
            for user in user_group.users.all():
                setattr(user, 'is_inherit_from_user_groups', True)
                setattr(user, 'inherit_from_user_groups',
                        getattr(user, 'inherit_from_user_groups', set()).add(user_group))
                users.add(user)
        return users

    def get_granted_assets(self):
        return list(set(self.assets.all()) | self.get_granted_asset_groups_member())

    def get_granted_asset_groups_member(self):
        assets = set()
        for asset_group in self.asset_groups.all():
            for asset in asset_group.assets.all():
                setattr(asset, 'is_inherit_from_asset_groups', True)
                setattr(asset, 'inherit_from_asset_groups',
                        getattr(asset, 'inherit_from_user_groups', set()).add(asset_group))
                assets.add(asset)
        return assets

    class Meta:
        db_table = 'asset_permission'


# def change_permission(sender, **kwargs):
#     print('Sender: %s' % sender)
#     for k, v in kwargs.items():
#         print('%s: %s' % (k, v))
#     print()

#
# m2m_changed.connect(change_permission, sender=AssetPermission.assets.through)



