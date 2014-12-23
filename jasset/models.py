from django.db import models
from juser.models import Group, User


class IDC(models.Model):
    name = models.CharField(max_length=80, unique=True)
    comment = models.CharField(max_length=100, blank=True, null=True)

    def __unicode__(self):
        return self.name


class Asset(models.Model):
    ip = models.IPAddressField(unique=True)
    port = models.SmallIntegerField(max_length=40)
    idc = models.ForeignKey(IDC)
    group = models.ManyToManyField(Group)
    ldap_enable = models.BooleanField(default=True)
    username_common = models.CharField(max_length=80, blank=True, null=True)
    password_common = models.CharField(max_length=160, blank=True, null=True)
    username_super = models.CharField(max_length=80, blank=True, null=True)
    password_super = models.CharField(max_length=160, blank=True, null=True)
    date_added = models.IntegerField(max_length=80)
    comment = models.CharField(max_length=100, blank=True, null=True)

    def __unicode__(self):
        return self.ip