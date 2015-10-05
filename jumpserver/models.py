# coding: utf-8

from django.db import models


class Setting(models.Model):
    default_user = models.CharField(max_length=100, null=True, blank=True)
    default_port = models.IntegerField(max_length=10, null=True, blank=True)
    default_pri_key_path = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = u'setting'
