# coding:utf-8
from __future__ import unicode_literals

from django.db import models


class AssetGroup(models.Model):
    name = models.CharField(max_length=64, unique=True)
    created_by = models.CharField(max_length=32, blank=True, verbose_name=u"创建者")
    comment = models.CharField(max_length=128, blank=True, null=True)

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = 'assetgroup'


class IDC(models.Model):
    name = models.CharField(max_length=32, verbose_name=u'机房名称')
    bandwidth = models.CharField(max_length=32, blank=True, verbose_name=u'机房带宽')
    contact = models.CharField(max_length=16, blank=True, verbose_name=u'联系人')
    phone = models.CharField(max_length=32, blank=True, verbose_name=u'联系电话')
    address = models.CharField(max_length=128, blank=True, verbose_name=u"机房地址")
    network = models.TextField(blank=True, verbose_name=u"IP地址段")
    date_added = models.DateField(auto_now=True, null=True)
    operator = models.CharField(max_length=32, blank=True, verbose_name=u"运营商")
    created_by = models.CharField(max_length=32, blank=True, verbose_name=u"创建者")
    comment = models.CharField(max_length=128, blank=True, verbose_name=u"备注")

    def __unicode__(self):
        return self.name

    class Meta:
        db_table = 'idc'
        verbose_name = u"IDC机房"
        verbose_name_plural = verbose_name


class AssetExtend(models.Model):
    pass


class Asset(models.Model):
    ip = models.CharField(max_length=32, blank=True, verbose_name="资产IP")
    other_ip = models.CharField(max_length=255, blank=True, verbose_name="其他IP")
    remote_card_ip = models.CharField(max_length=16, blank=True, verbose_name=u'远控卡IP')
    hostname = models.CharField(max_length=128, unique=True, blank=True, verbose_name=u"主机名")
    port = models.IntegerField(blank=True, verbose_name=u"端口")
    group = models.ManyToManyField(AssetGroup, blank=True, verbose_name=u"所属主机组")
    username = models.CharField(max_length=16, blank=True, verbose_name=u"管理用户名")
    password = models.CharField(max_length=256, blank=True, verbose_name=u"密码")
    idc = models.ForeignKey(IDC, blank=True, null=True, on_delete=models.SET_NULL, verbose_name=u'机房')
    mac_addr = models.CharField(max_length=20, blank=True, unique=True, verbose_name=u"MAC地址")
    brand = models.CharField(max_length=64, blank=True, verbose_name=u'硬件厂商型号')
    cpu = models.CharField(max_length=64, blank=True, verbose_name=u'CPU')
    memory = models.CharField(max_length=128, blank=True, verbose_name=u'内存')
    disk = models.CharField(max_length=1024, blank=True, verbose_name=u'硬盘')
    os = models.CharField(max_length=128, blank=True, verbose_name=u'系统信息')
    cabinet_no = models.CharField(max_length=32, blank=True, verbose_name=u'机柜号')
    cabinet_pos = models.IntegerField(null=True, blank=True, verbose_name=u'资产位置')
    number = models.CharField(max_length=32, blank=True, unique=True, verbose_name=u'资产编号')
    status = models.ManyToManyField(AssetExtend, blank=True,
                                    related_name="asset_status_extend", verbose_name="资产状态")
    type = models.ManyToManyField(AssetExtend, blank=True,
                                  related_name="asset_type_extend", verbose_name="资产类型")
    env = models.ManyToManyField(AssetExtend, blank=True,
                                 related_name="asset_env_extend", verbose_name="所属主机组环境")
    sn = models.CharField(max_length=128, blank=True, unique=True, verbose_name=u"SN编号")
    created_by = models.CharField(max_length=32, blank=True, verbose_name=u"创建者")
    is_active = models.BooleanField(default=True, verbose_name=u"是否激活")
    date_added = models.DateTimeField(auto_now=True, null=True)
    comment = models.CharField(max_length=128, blank=True, verbose_name=u"备注")

    def __unicode__(self):
        return self.ip

    class Meta:
        db_table = 'asset'











