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
    date_added = models.DateTimeField(auto_now=True)


class PermRule(models.Model):
    date_added = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=100)
    comment = models.CharField(max_length=100)
    asset = models.ManyToManyField(Asset)
    asset_group = models.ManyToManyField(AssetGroup)
    user = models.ManyToManyField(User)
    user_group = models.ManyToManyField(UserGroup)
    role = models.ManyToManyField(PermRole)
    ssh_type = models.BooleanField()
