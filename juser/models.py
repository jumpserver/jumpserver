#coding: utf-8

from django.db import models

from jasset.models import Asset, AssetGroup


class UserGroup(models.Model):
    name = models.CharField(max_length=80, unique=True)
    # assets = models.TextField(max_length=1000, verbose_name="Assets", default='')
    # asset_groups = models.CharField(max_length=1000, verbose_name="Asset Groups", default='')
    assets = models.ManyToManyField(Asset)
    asset_groups = models.ManyToManyField(AssetGroup)
    comment = models.CharField(max_length=160, blank=True, null=True)

    def __unicode__(self):
        return self.name

    def get_user(self):
        return self.user_set.all()

    def update(self, **kwargs):
        for key, value in kwargs.items():
            self.__setattr__(key, value)
            self.save()


class User(models.Model):
    USER_ROLE_CHOICES = (
        ('SU', 'SuperUser'),
        ('GA', 'GroupAdmin'),
        ('CU', 'CommonUser'),
    )
    username = models.CharField(max_length=80, unique=True)
    password = models.CharField(max_length=100)
    name = models.CharField(max_length=80)
    email = models.EmailField(max_length=75)
    role = models.CharField(max_length=2, choices=USER_ROLE_CHOICES, default='CU')
    uuid = models.CharField(max_length=100)
    group = models.ManyToManyField(UserGroup)
    assets = models.ManyToManyField(Asset)
    asset_groups = models.ManyToManyField(AssetGroup)
    ssh_key_pwd = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True)
    date_joined = models.DateTimeField(null=True)

    def __unicode__(self):
        return self.username

    def get_asset_group(self):
        """
        Get user host_groups.
        获取用户有权限的主机组
        """
        host_group_list = []
        perm_list = []
        user_group_all = self.group.all()
        for user_group in user_group_all:
            perm_list.extend(user_group.perm_set.all())

        for perm in perm_list:
            host_group_list.append(perm.asset_group)

        return host_group_list

    def get_asset_group_info(self, printable=False):
        """
        Get or print asset group info
        获取或打印用户授权资产组
        """
        asset_groups_info = {}
        asset_groups = self.get_asset_group()

        for asset_group in asset_groups:
            asset_groups_info[asset_group.id] = [asset_group.name, asset_group.comment]

        if printable:
            for group_id in asset_groups_info:
                if asset_groups_info[group_id][1]:
                    print "[%3s] %s -- %s" % (group_id,
                                              asset_groups_info[group_id][0],
                                              asset_groups_info[group_id][1])
                else:
                    print "[%3s] %s" % (group_id, asset_groups_info[group_id][0])
                print ''
        else:
            return asset_groups_info

    def get_asset(self):
        """
        Get the assets of under the user control.
        获取主机列表
        """
        assets = []
        asset_groups = self.get_asset_group()

        for asset_group in asset_groups:
            assets.extend(asset_group.asset_set.all())

        return assets

    def get_asset_info(self, printable=False):
        """
        Get or print the user asset info
        获取或打印用户资产信息
        """
        from jasset.models import AssetAlias
        assets_info = {}
        assets = self.get_asset()

        for asset in assets:
            asset_alias = AssetAlias.objects.filter(user=self, asset=asset)
            if asset_alias and asset_alias[0].alias != '':
                assets_info[asset.ip] = [asset.id, asset.ip, str(asset_alias[0].alias)]
            else:
                assets_info[asset.ip] = [asset.id, asset.ip, str(asset.comment)]

        if printable:
            ips = assets_info.keys()
            ips.sort()
            for ip in ips:
                if assets_info[ip][2]:
                    print '%-15s -- %s' % (ip, assets_info[ip][2])
                else:
                    print '%-15s' % ip
            print ''
        else:
            return assets_info

    def update(self, **kwargs):
        for key, value in kwargs.items():
            self.__setattr__(key, value)
            self.save()


class AdminGroup(models.Model):
    """
    under the user control group
    用户可以管理的用户组，或组的管理员是该用户
    """

    user = models.ForeignKey(User)
    group = models.ForeignKey(UserGroup)

    def __unicode__(self):
        return '%s: %s' % (self.user.username, self.group.name)


