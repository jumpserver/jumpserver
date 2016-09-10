from __future__ import unicode_literals, absolute_import

from django.db import models
from django.utils.translation import ugettext_lazy as _

from users.models import User, UserGroup
from assets.models import Asset, AssetGroup, SystemUser
from common.utils import date_expired_default


class UserAssetPerm(models.Model):
    user = models.ForeignKey(User, related_name='asset_perm', on_delete=models.CASCADE)
    assets = models.ManyToManyField(Asset, related_name='user_perms', blank=True)
    asset_groups = models.ManyToManyField(AssetGroup, related_name='user_perm', blank=True)
    system_users = models.ManyToManyField(SystemUser, related_name='user_perm', blank=True)
    date_expired = models.DateTimeField(default=date_expired_default, verbose_name=_('Date expired'))
    created_by = models.CharField(max_length=128)
    date_created = models.DateTimeField(auto_now=True)
    comment = models.TextField(verbose_name=_('Comment'))


class UserGroupAssetPerm(models.Model):
    pass
