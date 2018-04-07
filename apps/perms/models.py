import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from common.utils import date_expired_default


class ValidManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True) \
            .filter(date_start__lt=timezone.now())\
            .filter(date_expired__gt=timezone.now())


class AssetPermission(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    users = models.ManyToManyField('users.User', related_name='asset_permissions', blank=True, verbose_name=_("User"))
    user_groups = models.ManyToManyField('users.UserGroup', related_name='asset_permissions', blank=True, verbose_name=_("User group"))
    assets = models.ManyToManyField('assets.Asset', related_name='granted_by_permissions', blank=True, verbose_name=_("Asset"))
    nodes = models.ManyToManyField('assets.Node', related_name='granted_by_permissions', blank=True, verbose_name=_("Nodes"))
    system_users = models.ManyToManyField('assets.SystemUser', related_name='granted_by_permissions', verbose_name=_("System user"))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    date_start = models.DateTimeField(default=timezone.now, verbose_name=_("Date start"))
    date_expired = models.DateTimeField(default=date_expired_default, verbose_name=_('Date expired'))
    created_by = models.CharField(max_length=128, blank=True, verbose_name=_('Created by'))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_('Date created'))
    comment = models.TextField(verbose_name=_('Comment'), blank=True)

    objects = models.Manager()
    valid = ValidManager()
    inherit_from = None

    def __str__(self):
        return self.name

    @property
    def id_str(self):
        return str(self.id)

    @property
    def is_valid(self):
        if self.date_expired > timezone.now() > self.date_start and self.is_active:
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

    @property
    def users_detail(self):
        return " ".join([u.name for u in self.users.all()])

    @property
    def user_groups_detail(self):
        return " ".join([g.name for g in self.user_groups.all()])

    @property
    def assets_detail(self):
        return " ".join([a.hostname for a in self.assets.all()])

    @property
    def nodes_detail(self):
        return " ".join([g.value for g in self.nodes.all()])

    @property
    def system_users_detail(self):
        return " ".join([s.name for s in self.system_users.all()])

    @property
    def detail(self):
        data = ""
        if self.users.all():
            comment = _("User")
            users = "<b>{}: </b>".format(comment)
            for u in self.users.all():
                users += u.name + " "
            data += users + "<br/>"
        if self.assets.all():
            assets = _("<b>Assets: </b>")
            for a in self.assets.all():
                assets += a.hostname + " "
            data += assets + "<br/>"
        return data


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
