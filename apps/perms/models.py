import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from common.utils import date_expired_default


class AssetPermission(models.Model):
    from users.models import User, UserGroup
    from assets.models import Asset, AssetGroup, SystemUser, Cluster
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    users = models.ManyToManyField(User, related_name='asset_permissions', blank=True, verbose_name=_("User"))
    user_groups = models.ManyToManyField(UserGroup, related_name='asset_permissions', blank=True, verbose_name=_("User group"))
    assets = models.ManyToManyField(Asset, related_name='granted_by_permissions', blank=True, verbose_name=_("Asset"))
    asset_groups = models.ManyToManyField(AssetGroup, related_name='granted_by_permissions', blank=True, verbose_name=_("Asset group"))
    system_users = models.ManyToManyField(SystemUser, related_name='granted_by_permissions', verbose_name=_("System user"))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    date_expired = models.DateTimeField(default=date_expired_default, verbose_name=_('Date expired'))
    created_by = models.CharField(max_length=128, blank=True, verbose_name=_('Created by'))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_('Date created'))
    comment = models.TextField(verbose_name=_('Comment'), blank=True)

    def __str__(self):
        return self.name

    @property
    def is_valid(self):
        if self.date_expired > timezone.now() and self.is_active:
            return True
        return False

    def get_granted_users(self):
        return list(set(self.users.all()) | self.get_granted_user_groups_member())

    def get_granted_user_groups_member(self):
        users = set()
        for user_group in self.user_groups.all():
            for user in user_group.users.all():
                setattr(user, 'is_inherit_from_user_groups', True)
                setattr(user, 'inherit_from_user_groups',
                        getattr(user, 'inherit_from_user_groups', set()).add(user_group))
                users.add(user)
        return users

    def get_granted_assets(self):
        return list(set(self.assets.all()) | self.get_granted_asset_groups_member())

    def get_granted_asset_groups_member(self):
        assets = set()
        for asset_group in self.asset_groups.all():
            for asset in asset_group.assets.all():
                setattr(asset, 'is_inherit_from_asset_groups', True)
                setattr(asset, 'inherit_from_asset_groups',
                        getattr(asset, 'inherit_from_user_groups', set()).add(asset_group))
                assets.add(asset)
        return assets

    def check_system_user_in_assets(self):
        errors = {}
        assets = self.get_granted_assets()
        clusters = set([asset.cluster for asset in assets])
        for system_user in self.system_users.all():
            cluster_remain = clusters - set(system_user.cluster.all())
            if cluster_remain:
                errors[system_user] = cluster_remain
        return errors


class NodePermission(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    node = models.ForeignKey('assets.Node', on_delete=models.CASCADE, verbose_name=_("Node"))
    user_group = models.ForeignKey('users.UserGroup', on_delete=models.CASCADE, verbose_name=_("User group"))
    system_user = models.ForeignKey('assets.SystemUser', on_delete=models.CASCADE, verbose_name=_("System user"))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    date_expired = models.DateTimeField(default=date_expired_default, verbose_name=_('Date expired'))
    created_by = models.CharField(max_length=128, blank=True, verbose_name=_('Created by'))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_('Date created'))
    comment = models.TextField(verbose_name=_('Comment'), blank=True)

    def __str__(self):
        return "{}:{}:{}".format(self.node.value, self.user_group.name, self.system_user.name)

    class Meta:
        unique_together = ('node', 'user_group', 'system_user')
        verbose_name = _("Asset permission")
