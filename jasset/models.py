import datetime
from django.db import models
from juser.models import User, UserGroup


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


class Asset(models.Model):
    LOGIN_TYPE_CHOICES = (
        ('L', 'LDAP'),
        ('M', 'MAP'),
    )
    ip = models.IPAddressField(unique=True)
    port = models.IntegerField(max_length=6)
    idc = models.ForeignKey(IDC)
    bis_group = models.ManyToManyField(BisGroup)
    login_type = models.CharField(max_length=1, choices=LOGIN_TYPE_CHOICES, default='L')
    username = models.CharField(max_length=20, blank=True, null=True)
    password = models.CharField(max_length=80, blank=True, null=True)
    date_added = models.DateTimeField(auto_now=True, default=datetime.datetime.now(), null=True)
    is_active = models.BooleanField(default=True)
    comment = models.CharField(max_length=100, blank=True, null=True)

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
        return self.comment