from django.db import models
from juser.models import User
from jasset.models import Asset


class Permission(models.Model):
    USER_ROLE_CHOICES = (
        ('SU', 'SuperUser'),
        ('CU', 'CommonUser'),
    )
    user = models.ForeignKey(User)
    asset = models.ForeignKey(Asset)
    role = models.CharField(choices=USER_ROLE_CHOICES,
                            max_length=2,
                            blank=True,
                            null=True)

    def __unicode__(self):
        return '%s_%s' % (self.user.username, self.asset.ip)