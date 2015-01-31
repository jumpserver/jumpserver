from django.db import models
from juser.models import User, UserGroup
from jasset.models import Asset, BisGroup


class Perm(models.Model):
    user_group = models.ForeignKey(UserGroup)
    asset_group = models.ForeignKey(BisGroup)

    def __unicode__(self):
        return '%s_%s' % (self.user_group.name, self.asset_group.name)