from django.db import models
from juser.models import UserGroup, DEPT
from jasset.models import Asset, BisGroup


class Perm(models.Model):
    user_group = models.ForeignKey(UserGroup)
    asset_group = models.ForeignKey(BisGroup)

    def __unicode__(self):
        return '%s_%s' % (self.user_group.name, self.asset_group.name)


class CmdGroup(models.Model):
    name = models.CharField(max_length=50)
    cmd = models.CharField(max_length=999)
    dept = models.ForeignKey(DEPT)
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