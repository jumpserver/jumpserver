from django.db import models
from juser.models import User, UserGroup
from jasset.models import Asset, BisGroup


class Perm(models.Model):
    user_group = models.ForeignKey(UserGroup)
    asset_group = models.ForeignKey(BisGroup)

    def __unicode__(self):
        return '%s_%s' % (self.user_group.name, self.asset_group.name)


class CMD(models.Model):
    cmd = models.CharField(max_length=200)


class CmdGroup(models.Model):
    name = models.CharField(max_length=50)
    cmd = models.ForeignKey(CMD)
    comment = models.CharField(blank=True, null=True, max_length=50)


class SudoPerm(models.Model):
    user = models.CharField(max_length=100)
    is_user_group = models.BooleanField(default=False)
    asset = models.CharField(max_length=100)
    is_asset_group = models.BooleanField(default=False)
    cmd = models.CharField(max_length=200)
    is_cmd_group = models.BooleanField(default=False)

