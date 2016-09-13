from __future__ import unicode_literals, absolute_import
import functools

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from users.models import User, UserGroup
from assets.models import Asset, AssetGroup, SystemUser
from common.utils import date_expired_default, combine_seq


class AssetPermission(models.Model):
    ACTION_CHOICE = (
        ('1', 'Allow'),
        ('0', 'Deny'),
    )

    name = models.CharField(max_length=128, verbose_name=_('Name'))
    users = models.ManyToManyField(User, related_name='asset_permissions', blank=True)
    user_groups = models.ManyToManyField(UserGroup, related_name='asset_permissions', blank=True)
    assets = models.ManyToManyField(Asset, related_name='granted_by_permissions', blank=True)
    asset_groups = models.ManyToManyField(AssetGroup, related_name='granted_by_permissions', blank=True)
    system_users = models.ManyToManyField(SystemUser, related_name='granted_by_permissions')
    action = models.CharField(choices=ACTION_CHOICE, max_length=8, default='1')
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
    def set_inherit(obj):
        setattr(obj, 'inherited', True)
        return obj

    def get_granted_users(self):
        return list(set(self.users.all() or []) | set(self.get_granted_user_groups_member()))

    def get_granted_user_groups_member(self):
        combine_users = functools.partial(combine_seq, callback=AssetPermission.set_inherit)
        try:
            return functools.reduce(combine_users, [user_group.users.all()
                                                    for user_group in self.user_groups.iterator()])
        except TypeError:
            return []

    def get_granted_assets(self):
        return list(self.assets.all() or []) | set(self.get_granted_asset_groups_member())

    def get_granted_asset_groups_member(self):
        combine_assets = functools.partial(combine_seq, callback=AssetPermission.set_inherit)
        try:
            return functools.reduce(combine_assets, [asset_group.users.all()
                                                     for asset_group in self.asset_groups.iterator()])
        except TypeError:
            return []

    class Meta:
        db_table = 'asset_permission'

