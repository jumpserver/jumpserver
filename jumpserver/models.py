# coding: utf-8

from django.db import models


class Setting(models.Model):
    name = models.CharField(max_length=100)
    field1 = models.CharField(max_length=100, null=True, blank=True)
    field2 = models.CharField(max_length=100, null=True, blank=True)
    field3 = models.CharField(max_length=256, null=True, blank=True)
    field4 = models.CharField(max_length=100, null=True, blank=True)
    field5 = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = u'setting'

    def __unicode__(self):
        return self.name
