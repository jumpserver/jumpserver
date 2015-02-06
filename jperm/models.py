from django.db import models
from juser.models import User, UserGroup
from jasset.models import Asset, BisGroup


class Perm(models.Model):
    user_group = models.ForeignKey(UserGroup)
    asset_group = models.ForeignKey(BisGroup)

    def __unicode__(self):
        return '%s_%s' % (self.user_group.name, self.asset_group.name)


class CmdGroup(models.Model):
    name = models.CharField(max_length=50)
    cmd = models.CharField(max_length=999)
    comment = models.CharField(blank=True, null=True, max_length=50)


class SudoPerm(models.Model):
    user_group = models.ManyToManyField(UserGroup)
    asset_group = models.ManyToManyField(BisGroup)
    cmd_group = models.ManyToManyField(CmdGroup)
    comment = models.CharField(max_length=30)