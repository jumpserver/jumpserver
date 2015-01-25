from django.db import models
from juser.models import User
from jasset.models import Asset


class Perm(models.Model):
    user = models.ForeignKey(User)
    asset = models.ForeignKey(Asset)

    def __unicode__(self):
        return '%s_%s' % (self.user.username, self.asset.ip)