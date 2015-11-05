import datetime

from django.db import models
from jasset.models import Asset, AssetGroup
from juser.models  import User, UserGroup


class PermLog(models.Model):
    datetime = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=100, null=True, blank=True, default='')
    results = models.CharField(max_length=1000, null=True, blank=True, default='')
    is_success = models.BooleanField(default=False)
    is_finish = models.BooleanField(default=False)


class SysUser(models.Model):
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100)
    comment = models.CharField(max_length=100, null=True, blank=True, default='')


class PermRole(models.Model):
    name = models.CharField(max_length=100)
    comment = models.CharField(max_length=100)


class UserMapping(models.Model):
    role = models.ForeignKey(PermRole, related_name='user_mapping')
    user = models.ForeignKey(User, related_name='user_mapping')
    asset = models.ForeignKey(Asset, related_name='user_mapping')
    asset_group = models.ForeignKey(AssetGroup, related_name='user_mapping', null=True, blank=True)


class GroupMapping(models.Model):
    role = models.ForeignKey(PermRole, related_name='group_mapping')
    usergroup = models.ForeignKey(UserGroup, related_name='group_mapping', null=True, blank=True)
    asset = models.ForeignKey(Asset, related_name='group_mapping')
    asset_group = models.ForeignKey(AssetGroup, related_name='group_mapping', null=True, blank=True)







