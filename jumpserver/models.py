# coding: utf-8

from django.db import models


class Setting(models.Model):
    name = models.CharField(max_length=100)
    default_user = models.CharField(max_length=100, null=True, blank=True)
    default_port = models.IntegerField(null=True, blank=True)
    default_password = models.CharField(max_length=100, null=True, blank=True)
    default_pri_key_path = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = u'setting'
