# coding: utf-8

import datetime
from django.db import models
from juser.models import User, UserGroup


class AssetGroup(models.Model):
    GROUP_TYPE = (
        ('P', 'PRIVATE'),
        ('A', 'ASSET'),
    )
    name = models.CharField(max_length=80, unique=True)
    comment = models.CharField(max_length=160, blank=True, null=True)

    def __unicode__(self):
        return self.name

    def get_asset(self):
        return self.asset_set.all()

    def get_asset_info(self, printable=False):
        assets = self.get_asset()
        ip_comment = {}
        for asset in assets:
            ip_comment[asset.ip] = asset.comment

        for ip in sorted(ip_comment):
            if ip_comment[ip]:
                print '%-15s -- %s' % (ip, ip_comment[ip])
            else:
                print '%-15s' % ip
        print ''

    def get_asset_num(self):
        return len(self.get_asset())

    def get_user_group(self):
        perm_list = self.perm_set.all()
        user_group_list = []
        for perm in perm_list:
            user_group_list.append(perm.user_group)
        return user_group_list

    def get_user(self):
        user_list = []
        user_group_list = self.get_user_group()
        for user_group in user_group_list:
            user_list.extend(user_group.user_set.all())
        return user_list

    def is_permed(self, user=None, user_group=None):
        if user:
            if user in self.get_user():
                return True

        if user_group:
            if user_group in self.get_user_group():
                return True
        return False


class IDC(models.Model):
    name = models.CharField(max_length=32, verbose_name=u'机房名称')
    bandwidth = models.CharField(max_length=32, blank=True, null=True, verbose_name=u'机房带宽')
    linkman = models.CharField(max_length=16, null=True, verbose_name=u'联系人')
    phone = models.CharField(max_length=32, verbose_name=u'联系电话')
    address = models.CharField(max_length=128, blank=True, null=True, verbose_name=u"机房地址")
    network = models.TextField(blank=True, null=True, verbose_name=u"IP地址段")
    date_added = models.DateField(auto_now=True, default=datetime.datetime.now(), null=True)
    operator = models.IntegerField(max_length=32, blank=True, null=True, verbose_name=u"运营商")
    comment = models.TextField(blank=True, null=True, verbose_name=u"备注")

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = u"IDC机房"
        verbose_name_plural = verbose_name


class Asset(models.Model):
    """
    asset modle
    """
    ENVIRONMENT = (
        (0, U'生产环境'),
        (1, U'测试环境')
    )
    SERVER_STATUS = (
        (0, u"已使用"),
        (1, u"未使用"),
        (2, u"报废")
    )
    ASSET_TYPE = (
        (0, u"服务器"),
        (2, u"网络设备"),
        (3, u"其他")
    )

    ip = models.IPAddressField(unique=True, verbose_name=u"主机IP")
    second_ip = models.IPAddressField(unique=True, blank=True, null=True, verbose_name=u"IP2")
    hostname = models.CharField(max_length=64, blank=True, null=True, verbose_name=u"主机名")
    port = models.IntegerField(max_length=6, verbose_name=u"端口号")
    group = models.ManyToManyField(AssetGroup, blank=True, null=True, verbose_name=u"所属主机组")
    username = models.CharField(max_length=16, blank=True, null=True, verbose_name=u"管理用户名")
    password = models.CharField(max_length=64, blank=True, null=True, verbose_name=u"密码")
    use_default_auth = models.BooleanField(default=True, verbose_name=u"使用默认管理账号")
    idc = models.ForeignKey(IDC, blank=True, null=True,  on_delete=models.SET_NULL, verbose_name=u'机房')
    mac = models.CharField(max_length=20, blank=True, null=True, verbose_name=u"MAC地址")
    remote_ip = models.IPAddressField(unique=True, blank=True, null=True, verbose_name=u'远控卡')
    brand = models.CharField(max_length=64, blank=True, null=True, verbose_name=u'硬件厂商型号')
    cpu = models.CharField(max_length=64, blank=True, null=True, verbose_name=u'CPU')
    memory = models.CharField(max_length=128, blank=True, null=True, verbose_name=u'内存')
    disk = models.CharField(max_length=128, blank=True, null=True, verbose_name=u'硬盘')
    system_type = models.CharField(max_length=32, blank=True, null=True, verbose_name=u"系统类型")
    system_version = models.CharField(max_length=8, blank=True, null=True, verbose_name=u"版本号")
    cabinet = models.CharField(max_length=32, blank=True, null=True, verbose_name=u'机柜号')
    position = models.IntegerField(max_length=2, blank=True, null=True, verbose_name=u'机器位置')
    number = models.CharField(max_length=32, blank=True, null=True, verbose_name=u'资产编号')
    status = models.IntegerField(max_length=2, choices=SERVER_STATUS, default=1, verbose_name=u"机器状态")
    asset_type = models.IntegerField(max_length=2, choices=ASSET_TYPE, blank=True, null=True, verbose_name=u"主机类型")
    env = models.CharField(max_length=32, choices=ENVIRONMENT, blank=True, null=True, verbose_name=u"运行环境")
    sn = models.CharField(max_length=32, blank=True, null=True, verbose_name=u"SN编号")
    date_added = models.DateTimeField(auto_now=True, default=datetime.datetime.now(), null=True)
    is_active = models.BooleanField(default=True, verbose_name=u"是否激活")
    comment = models.CharField(max_length=128, blank=True, null=True, verbose_name=u"备注")

    def __unicode__(self):
        return self.ip

    def get_user(self):
        perm_list = []
        asset_group_all = self.bis_group.all()
        for asset_group in asset_group_all:
            perm_list.extend(asset_group.perm_set.all())

        user_group_list = []
        for perm in perm_list:
            user_group_list.append(perm.user_group)

        user_permed_list = []
        for user_group in user_group_list:
            user_permed_list.extend(user_group.user_set.all())
        user_permed_list = list(set(user_permed_list))
        return user_permed_list


class AssetAlias(models.Model):
    user = models.ForeignKey(User)
    asset = models.ForeignKey(Asset)
    alias = models.CharField(max_length=100, blank=True, null=True)

    def __unicode__(self):
        return self.alias
