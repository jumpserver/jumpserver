from __future__ import unicode_literals, absolute_import

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from users.models import User, UserGroup
from assets.models import Asset, AssetGroup, SystemUser
from common.utils import date_expired_default


class PermUserAsset(models.Model):
    ACTION_CHOICE = (
        ('1', 'Allow'),
        ('0', 'Deny'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(choices=ACTION_CHOICE, max_length=8, default='1')
    assets = models.ManyToManyField(Asset, blank=True)
    asset_groups = models.ManyToManyField(AssetGroup,  blank=True)
    system_users = models.ManyToManyField(SystemUser,  blank=True)
    date_expired = models.DateTimeField(default=date_expired_default, verbose_name=_('Date expired'))
    created_by = models.CharField(max_length=128, blank=True)
    date_created = models.DateTimeField(auto_now=True)
    comment = models.TextField(verbose_name=_('Comment'))

    def __unicode__(self):
        return '%(id)s: %(user)s %(action)s' % {
            'id': self.id,
            'user': self.user.username,
            'action': self.action,
        }

    @property
    def is_expired(self):
        if self.date_expired > timezone.now():
            return False
        else:
            return True

    class Meta:
        db_table = 'perm_user_asset'


class PermUserGroupAsset(models.Model):
    ACTION_CHOICES = (
        ('0', 'Deny'),
        ('1', 'Allow'),
    )

    user_group = models.ForeignKey(User,  on_delete=models.CASCADE)
    action = models.CharField(choices=ACTION_CHOICES, max_length=8, default='1')
    assets = models.ManyToManyField(Asset, blank=True)
    asset_groups = models.ManyToManyField(AssetGroup, blank=True)
    system_users = models.ManyToManyField(SystemUser, blank=True)
    date_expired = models.DateTimeField(default=date_expired_default, verbose_name=_('Date expired'))
    created_by = models.CharField(max_length=128)
    date_created = models.DateTimeField(auto_now=True)
    comment = models.TextField(verbose_name=_('Comment'))

    def __unicode__(self):
        return '%(id)s: %(user)s %(action)s' % {
            'id': self.id,
            'user': self.user_group.name,
            'action': self.action,
        }

    @property
    def is_expired(self):
        if self.date_expired > timezone.now():
            return False
        else:
            return True

    class Meta:
        db_table = 'perm_user_group_asset'

