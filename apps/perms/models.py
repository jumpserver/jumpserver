from __future__ import unicode_literals, absolute_import

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from users.models import User, UserGroup
from assets.models import Asset, AssetGroup, SystemUser
from common.utils import date_expired_default


class AssetPermission(models.Model):
    ACTION_CHOICE = (
        ('1', 'Allow'),
        ('0', 'Deny'),
    )

    name = models.CharField(max_length=128, verbose_name=_('Name'))
    users = models.ManyToManyField(User, related_name='asset_permissions')
    user_groups = models.ManyToManyField(UserGroup, related_name='asset_permissions')
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

    class Meta:
        db_table = 'asset_permission'

