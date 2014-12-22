from django.db import models
from juser.models import User
from jasset.models import Asset


class Permission(models.Model):
    PERM_USER_TYPE_CHOICE = (
        ('S', 'Super'),
        ('C', 'Common'),
    )
    user = models.ForeignKey(User)
    asset = models.ForeignKey(Asset)
    is_ldap = models.BooleanField(default=True)
    perm_user_type = models.CharField(choices=PERM_USER_TYPE_CHOICE,
                                      max_length=1,
                                      blank=True,
                                      null=True)

    def __unicode__(self):
        return '%s_%s' % (self.user.username, self.asset.ip)