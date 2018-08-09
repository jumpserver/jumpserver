import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from common.utils import date_expired_default, set_or_append_attr_bulk

from orgs.mixins import OrgModelMixin, OrgManager


class AssetPermissionQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def valid(self):
        return self.active().filter(date_start__lt=timezone.now())\
            .filter(date_expired__gt=timezone.now())


class AssetPermissionManager(OrgManager):
    def valid(self):
        return self.get_queryset().valid()


class AssetPermission(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    users = models.ManyToManyField('users.User', related_name='asset_permissions', blank=True, verbose_name=_("User"))
    user_groups = models.ManyToManyField('users.UserGroup', related_name='asset_permissions', blank=True, verbose_name=_("User group"))
    assets = models.ManyToManyField('assets.Asset', related_name='granted_by_permissions', blank=True, verbose_name=_("Asset"))
    nodes = models.ManyToManyField('assets.Node', related_name='granted_by_permissions', blank=True, verbose_name=_("Nodes"))
    system_users = models.ManyToManyField('assets.SystemUser', related_name='granted_by_permissions', verbose_name=_("System user"))
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    date_start = models.DateTimeField(default=timezone.now, db_index=True, verbose_name=_("Date start"))
    date_expired = models.DateTimeField(default=date_expired_default, db_index=True, verbose_name=_('Date expired'))
    created_by = models.CharField(max_length=128, blank=True, verbose_name=_('Created by'))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_('Date created'))
    comment = models.TextField(verbose_name=_('Comment'), blank=True)

    objects = AssetPermissionManager.from_queryset(AssetPermissionQuerySet)()

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _("Asset permission")

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

    def get_all_users(self):
        users = set(self.users.all())
        for group in self.user_groups.all():
            _users = group.users.all()
            set_or_append_attr_bulk(_users, 'inherit', group.name)
            users.update(set(_users))
        return users

    def get_all_assets(self):
        assets = set(self.assets.all())
        for node in self.nodes.all():
            _assets = node.get_all_assets()
            set_or_append_attr_bulk(_assets, 'inherit', node.value)
            assets.update(set(_assets))
        return assets


class NodePermission(OrgModelMixin):
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
        verbose_name = _("Asset permission")
