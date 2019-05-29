import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils import date_expired_default, set_or_append_attr_bulk
from orgs.mixins import OrgModelMixin

from ..const import PERMS_ACTION_NAME_CHOICES, PERMS_ACTION_NAME_ALL
from .base import BasePermission


__all__ = [
    'Action', 'AssetPermission', 'NodePermission',
]


class Action(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(
        max_length=128, unique=True, choices=PERMS_ACTION_NAME_CHOICES,
        verbose_name=_('Name')
    )

    class Meta:
        verbose_name = _('Action')

    def __str__(self):
        return self.get_name_display()

    @classmethod
    def get_action_all(cls):
        return cls.objects.get(name=PERMS_ACTION_NAME_ALL)


class AssetPermission(BasePermission):
    assets = models.ManyToManyField('assets.Asset', related_name='granted_by_permissions', blank=True, verbose_name=_("Asset"))
    nodes = models.ManyToManyField('assets.Node', related_name='granted_by_permissions', blank=True, verbose_name=_("Nodes"))
    system_users = models.ManyToManyField('assets.SystemUser', related_name='granted_by_permissions', verbose_name=_("System user"))
    actions = models.ManyToManyField('Action', related_name='permissions', blank=True, verbose_name=_('Action'))

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _("Asset permission")

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
