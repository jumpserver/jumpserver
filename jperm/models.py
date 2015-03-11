from django.db import models
from juser.models import User, UserGroup, DEPT
from jasset.models import Asset, BisGroup


class Perm(models.Model):
    user = models.ForeignKey(User)
    asset = models.ForeignKey(Asset)

    def __unicode__(self):
        return '%s_%s' % (self.user.name, self.asset.ip)


class DeptPerm(models.Model):
    dept = models.ForeignKey(DEPT)
    asset = models.ForeignKey(Asset)

    def __unicode__(self):
        return '%s_%s' % (self.dept.name, self.asset.ip)


class ShowPerm(models.Model):
    uid = models.CharField(max_length=500, blank=True, null=True)
    gid = models.CharField(max_length=500, blank=True, null=True)
    did = models.CharField(max_length=500, blank=True, null=True)
    aid = models.CharField(max_length=500, blank=True, null=True)
    bid = models.CharField(max_length=500, blank=True, null=True)
    comment = models.CharField(max_length=200, blank=True, null=True)


class CmdGroup(models.Model):
    name = models.CharField(max_length=50)
    cmd = models.CharField(max_length=999)
    comment = models.CharField(blank=True, null=True, max_length=50)

    def __unicode__(self):
        return self.name


class SudoPerm(models.Model):
    name = models.CharField(max_length=20)
    user_runas = models.CharField(max_length=100)
    user_group = models.ManyToManyField(UserGroup)
    asset_group = models.ManyToManyField(BisGroup)
    cmd_group = models.ManyToManyField(CmdGroup)
    comment = models.CharField(max_length=30, null=True, blank=True)

    def __unicode__(self):
        return self.name