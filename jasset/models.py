import datetime
from django.db import models
from juser.models import UserGroup, DEPT


class IDC(models.Model):
    name = models.CharField(max_length=40, unique=True)
    comment = models.CharField(max_length=80, blank=True, null=True)

    def __unicode__(self):
        return self.name


class BisGroup(models.Model):
    GROUP_TYPE = (
        ('P', 'PRIVATE'),
        ('A', 'ASSET'),
    )
    name = models.CharField(max_length=80, unique=True)
    dept = models.ForeignKey(DEPT)
    comment = models.CharField(max_length=160, blank=True, null=True)
    type = models.CharField(max_length=1, choices=GROUP_TYPE, default='P')

    def __unicode__(self):
        return self.name


class Asset(models.Model):
    LOGIN_TYPE_CHOICES = (
        ('L', 'LDAP'),
        ('M', 'MAP'),
    )
    ip = models.IPAddressField(unique=True)
    port = models.SmallIntegerField(max_length=5)
    idc = models.ForeignKey(IDC)
    bis_group = models.ManyToManyField(BisGroup)
    dept = models.ManyToManyField(DEPT)
    login_type = models.CharField(max_length=1, choices=LOGIN_TYPE_CHOICES, default='L')
    username = models.CharField(max_length=20, blank=True, null=True)
    password = models.CharField(max_length=80, blank=True, null=True)
    date_added = models.DateTimeField(auto_now=True, default=datetime.datetime.now(), null=True)
    is_active = models.BooleanField(default=True)
    comment = models.CharField(max_length=100, blank=True, null=True)

    def __unicode__(self):
        return self.ip