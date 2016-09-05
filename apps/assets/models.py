# coding:utf-8
from __future__ import unicode_literals, absolute_import

from django.db import models
from django.utils.translation import ugettext_lazy as _


class AssetGroup(models.Model):
    name = models.CharField(max_length=64, unique=True, null=True, blank=True, verbose_name=_('Name'))
    created_by = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Created by'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))

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
    comment = models.TextField(blank=True, verbose_name=_('Comment'))

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = 'idc'


class AssetExtend(models.Model):
    key = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('KEY'))
    value = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('VALUE'))
    created_by = models.CharField(max_length=32, blank=True, verbose_name=_("Created by"))
    date_added = models.DateTimeField(auto_now=True, null=True, blank=True)
    comment = models.TextField(blank=True, verbose_name=_('Comment'))

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = 'assetextend'


class AdminUser(models.Model):
    name = models.CharField(max_length=128, unique=True, null=True, blank=True, verbose_name=_('Name'))
    username = models.CharField(max_length=16, null=True, blank=True, verbose_name=_('Username'))
    password = models.CharField(max_length=256, null=True, blank=True, verbose_name=_('Password'))
    private_key = models.CharField(max_length=4096, null=True, blank=True, verbose_name=_('SSH private key'))
    is_default = models.BooleanField(default=True, verbose_name=_('As default'))
    auto_update = models.BooleanField(default=True, verbose_name=_('Auto update pass/key'))
    date_added = models.DateTimeField(auto_now=True, null=True, blank=True)
    create_by = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Created by'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = 'adminuser'


class SysUser(models.Model):
    PROTOCOL_CHOICES = (
        ('ssh', 'ssh'),
        ('telnet', 'telnet'),
    )
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    username = models.CharField(max_length=16, blank=True, verbose_name=_('Username'))
    password = models.CharField(max_length=256, blank=True, verbose_name=_('Password'))
    protocol = models.CharField(max_length=16, default='ssh', verbose_name=_('Protocol'))
    private_key = models.CharField(max_length=4096, blank=True, verbose_name=_('SSH private key'))
    public_key = models.CharField(max_length=4096, blank=True, verbose_name=_('SSH public key'))
    is_default = models.BooleanField(default=True, verbose_name=_('As default'))
    auto_push = models.BooleanField(default=True, verbose_name=_('Auto push'))
    auto_update = models.BooleanField(default=True, verbose_name=_('Auto update pass/key'))
    sudo = models.TextField(max_length=4096, blank=True, verbose_name=_('Sudo'))
    shell = models.CharField(max_length=64,  blank=True, verbose_name=_('Shell'))
    home = models.CharField(max_length=64, blank=True, verbose_name=_('Home'))
    uid = models.IntegerField(blank=True, verbose_name=_('Uid'))
    date_added = models.DateTimeField(auto_now=True, null=True)
    create_by = models.CharField(max_length=32, blank=True, verbose_name=_('Created by'))
    comment = models.CharField(max_length=128, blank=True, verbose_name=_('Comment'))

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = 'sysuser'


class Asset(models.Model):
    ip = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('IP'))
    other_ip = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Other IP'))
    remote_card_ip = models.CharField(max_length=16, null=True, blank=True, verbose_name=_('Remote card IP'))
    hostname = models.CharField(max_length=128, unique=True, null=True, blank=True, verbose_name=_('Hostname'))
    port = models.IntegerField(null=True, blank=True, verbose_name=_('Port'))
    groups = models.ManyToManyField(AssetGroup, null=True, blank=True, verbose_name=_('Asset groups'))
    username = models.CharField(max_length=16, null=True, blank=True, verbose_name=_('Admin user'))
    password = models.CharField(max_length=256, null=True, blank=True, verbose_name=_("Admin password"))
    admin_user = models.ForeignKey(AdminUser, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("Admin user"))
    sys_user = models.ManyToManyField(SysUser, null=True, blank=True, verbose_name=_("System User"))
    idc = models.ForeignKey(IDC, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_('IDC'))
    mac_addr = models.CharField(max_length=20, null=True, blank=True, verbose_name=_("Mac address"))
    brand = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('Brand'))
    cpu = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('CPU'))
    memory = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('Memory'))
    disk = models.CharField(max_length=1024, null=True, blank=True, verbose_name=_('Disk'))
    os = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('OS'))
    cabinet_no = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Cabinet number'))
    cabinet_pos = models.IntegerField(null=True, blank=True, verbose_name=_('Cabinet position'))
    number = models.CharField(max_length=32, null=True, blank=True, unique=True, verbose_name=_('Asset number'))
    status = models.ManyToManyField(AssetExtend, related_name="asset_status_extend", verbose_name=_('Asset status'))
    type = models.ManyToManyField(AssetExtend, related_name="asset_type_extend", verbose_name=_('Asset type'))
    env = models.ManyToManyField(AssetExtend,  related_name="asset_env_extend", verbose_name=_('Asset environment'))
    sn = models.CharField(max_length=128, null=True, blank=True, unique=True, verbose_name=_('Serial number'))
    created_by = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Created by'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))
    date_added = models.DateTimeField(auto_now=True, null=True, blank=True, verbose_name=_('Date added'))
    comment = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('Comment'))

    def __unicode__(self):
        return '%(ip)s:%(port)d' % {'ip': self.ip, 'port': self.port}

    def initial(self):
        pass

    class Meta:
        db_table = 'asset'
        index_together = ('ip', 'port')


class Label(models.Model):
    key = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('KEY'))
    value = models.CharField(max_length=64, null=True, blank=True, verbose_name=_('VALUE'))
    asset = models.ForeignKey(Asset, null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_('Asset'))
    created_by = models.CharField(max_length=32, blank=True, verbose_name=_("Created by"))
    date_added = models.DateTimeField(auto_now=True, null=True)
    comment = models.CharField(max_length=128, blank=True, verbose_name=_('Comment'))

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = 'label'

