# coding:utf-8
from __future__ import unicode_literals, absolute_import

from django.db import models
from django.utils.translation import ugettext_lazy as _


class AssetGroup(models.Model):
    name = models.CharField(max_length=64, unique=True, verbose_name=_('Name'))
    created_by = models.CharField(max_length=32, blank=True, verbose_name=_('Created by'))
    comment = models.CharField(max_length=128, blank=True, verbose_name=_('Comment'))

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = 'assetgroup'


class IDC(models.Model):
    name = models.CharField(max_length=32, verbose_name=_('Name'))
    bandwidth = models.CharField(max_length=32, blank=True, verbose_name=_('Bandwidth'))
    contact = models.CharField(max_length=16, blank=True, verbose_name=_('Contact'))
    phone = models.CharField(max_length=32, blank=True, verbose_name=_('Phone'))
    address = models.CharField(max_length=128, blank=True, verbose_name=_("Address"))
    network = models.TextField(blank=True, verbose_name=_('Network'))
    date_added = models.DateField(auto_now=True, null=True, verbose_name=_('Date added'))
    operator = models.CharField(max_length=32, blank=True, verbose_name=_('Operator'))
    created_by = models.CharField(max_length=32, blank=True, verbose_name=_('Created by'))
    comment = models.CharField(max_length=128, blank=True, verbose_name=_('Comment'))

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = 'idc'
        verbose_name = _('IDC')
        verbose_name_plural = verbose_name


class AssetExtend(models.Model):
    pass


class Asset(models.Model):
    ip = models.CharField(max_length=32, blank=True, verbose_name=_('IP'))
    other_ip = models.CharField(max_length=255, blank=True, verbose_name=_('Other IP'))
    remote_card_ip = models.CharField(max_length=16, blank=True, verbose_name=_('Remote card IP'))
    hostname = models.CharField(max_length=128, unique=True, blank=True, verbose_name=_('Hostname'))
    port = models.IntegerField(blank=True, verbose_name=_('Port'))
    groups = models.ManyToManyField(AssetGroup, blank=True, verbose_name=_('Asset groups'))
    username = models.CharField(max_length=16, blank=True, verbose_name=_('Admin user'))
    password = models.CharField(max_length=256, blank=True, verbose_name=_("Admin password"))
    idc = models.ForeignKey(IDC, blank=True, null=True, on_delete=models.SET_NULL, verbose_name=_('IDC'))
    mac_addr = models.CharField(max_length=20, blank=True, verbose_name=_("Mac address"))
    brand = models.CharField(max_length=64, blank=True, verbose_name=_('Brand'))
    cpu = models.CharField(max_length=64, blank=True, verbose_name=_('CPU'))
    memory = models.CharField(max_length=128, blank=True, verbose_name=_('Memory'))
    disk = models.CharField(max_length=1024, blank=True, verbose_name=_('Disk'))
    os = models.CharField(max_length=128, blank=True, verbose_name=_('OS'))
    cabinet_no = models.CharField(max_length=32, blank=True, verbose_name=_('Cabinet number'))
    cabinet_pos = models.IntegerField(null=True, blank=True, verbose_name=_('Cabinet position'))
    number = models.CharField(max_length=32, blank=True, unique=True, verbose_name=_('Asset number'))
    status = models.ManyToManyField(AssetExtend, blank=True,
                                    related_name="asset_status_extend", verbose_name=_('Asset status'))
    type = models.ManyToManyField(AssetExtend, blank=True,
                                  related_name="asset_type_extend", verbose_name=_('Asset type'))
    env = models.ManyToManyField(AssetExtend, blank=True,
                                 related_name="asset_env_extend", verbose_name=_('Asset environment'))
    sn = models.CharField(max_length=128, blank=True, unique=True, verbose_name=_('Serial number'))
    created_by = models.CharField(max_length=32, blank=True, verbose_name=_('Created by'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))
    date_added = models.DateTimeField(auto_now=True, null=True, verbose_name=_('Date added'))
    comment = models.CharField(max_length=128, blank=True, verbose_name=_('Comment'))

    def __unicode__(self):
        return self.ip

    class Meta:
        db_table = 'asset'

