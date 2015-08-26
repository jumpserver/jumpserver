import datetime

from uuidfield import UUIDField

from django.db import models
from juser.models import UserGroup
from jasset.models import Asset, BisGroup


class Perm(models.Model):
    user_group = models.ForeignKey(UserGroup)
    asset_group = models.ForeignKey(BisGroup)

    def __unicode__(self):
        return '%s_%s' % (self.user_group.name, self.asset_group.name)


class CmdGroup(models.Model):
    name = models.CharField(max_length=50, unique=True)
    cmd = models.CharField(max_length=999)
    comment = models.CharField(blank=True, null=True, max_length=50)

    def __unicode__(self):
        return self.name


class SudoPerm(models.Model):
    user_group = models.ForeignKey(UserGroup)
    user_runas = models.CharField(max_length=100)
    asset_group = models.ManyToManyField(BisGroup)
    cmd_group = models.ManyToManyField(CmdGroup)
    comment = models.CharField(max_length=30, null=True, blank=True)

    def __unicode__(self):
        return self.user_group.name


class Apply(models.Model):
    uuid = UUIDField(auto=True)
    applyer = models.CharField(max_length=20)
    admin = models.CharField(max_length=20)
    approver = models.CharField(max_length=20)
    bisgroup = models.CharField(max_length=500)
    asset = models.CharField(max_length=500)
    comment = models.TextField(blank=True, null=True)
    status = models.IntegerField(max_length=2)
    date_add = models.DateTimeField(null=True)
    date_end = models.DateTimeField(null=True)
    read = models.IntegerField(max_length=2)

    def __unicode__(self):
        return self.applyer
