from django.db import models
from juser.models import User, UserGroup
from jasset.models import Asset, BisGroup


class PermUser(models.Model):
    user = models.ForeignKey(User)
    asset = models.ForeignKey(Asset)
    asset_group = models.ForeignKey(BisGroup)

    def __unicode__(self):
        return '%s_%s' % (self.user.username, self.asset.ip)


class PermUserGroup(models.Model):
    group = models.ForeignKey(UserGroup)
    asset = models.ForeignKey(Asset)
    asset_group = models.ForeignKey(BisGroup)

    def __unicode__(self):
        return '%s_%s' % (self.group.name, self.asset.ip)