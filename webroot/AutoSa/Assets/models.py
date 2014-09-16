from django.db import models
from UserManage.models import User


class Assets(models.Model):
    id = models.AutoField(primary_key=True)
    ip = models.CharField(max_length=20)
    port = models.IntegerField(max_length=5)
    idc = models.CharField(max_length=50)
    comment = models.CharField(max_length=100, blank=True, null=True)

    def __unicode__(self):
        return '%s ' % self.ip


class AssetsUser(models.Model):
    uid = models.ForeignKey(User)
    aid = models.ForeignKey(Assets)