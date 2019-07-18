import uuid
from functools import reduce

from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from common.utils import date_expired_default, set_or_append_attr_bulk
from orgs.mixins import OrgModelMixin
from assets.models import Asset, SystemUser, Node

from .base import BasePermission


__all__ = [
    'AssetPermission', 'NodePermission', 'Action',
]


class Action:
    NONE = 0
    CONNECT = 0b00000001
    UPLOAD = 0b00000010
    DOWNLOAD = 0b00000100
    UPDOWNLOAD = UPLOAD | DOWNLOAD
    ALL = 0b11111111

    DB_CHOICES = (
        (ALL, _('All')),
        (CONNECT, _('Connect')),
        (UPLOAD, _('Upload file')),
        (DOWNLOAD, _('Download file')),
        (UPDOWNLOAD, _("Upload download")),
    )

    NAME_MAP = {
        ALL: "all",
        CONNECT: "connect",
        UPLOAD: "upload_file",
        DOWNLOAD: "download_file",
        UPDOWNLOAD: "updownload",
    }

    NAME_MAP_REVERSE = dict({v: k for k, v in NAME_MAP.items()})
    CHOICES = []
    for i, j in DB_CHOICES:
        CHOICES.append((NAME_MAP[i], j))

    @classmethod
    def value_to_choices(cls, value):
        value = int(value)
        choices = [cls.NAME_MAP[i] for i, j in cls.DB_CHOICES if value & i == i]
        return choices

    @classmethod
    def choices_to_value(cls, value):
        if not isinstance(value, list):
            return cls.NONE
        db_value = [
            cls.NAME_MAP_REVERSE[v] for v in value
            if v in cls.NAME_MAP_REVERSE.keys()
        ]
        if not db_value:
            return cls.NONE

        def to_choices(x, y):
            return x | y

        result = reduce(to_choices, db_value)
        return result

    @classmethod
    def choices(cls):
        return [(cls.NAME_MAP[i], j) for i, j in cls.DB_CHOICES]


class AssetPermission(BasePermission):
    assets = models.ManyToManyField('assets.Asset', related_name='granted_by_permissions', blank=True, verbose_name=_("Asset"))
    nodes = models.ManyToManyField('assets.Node', related_name='granted_by_permissions', blank=True, verbose_name=_("Nodes"))
    system_users = models.ManyToManyField('assets.SystemUser', related_name='granted_by_permissions', verbose_name=_("System user"))
    # actions = models.ManyToManyField(Action, related_name='permissions', blank=True, verbose_name=_('Action'))
    actions = models.IntegerField(choices=Action.DB_CHOICES, default=Action.ALL, verbose_name=_("Actions"))

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _("Asset permission")

    @classmethod
    def get_queryset_with_prefetch(cls):
        return cls.objects.all().valid().prefetch_related(
            models.Prefetch('nodes', queryset=Node.objects.all().only('key')),
            models.Prefetch('assets', queryset=Asset.objects.all().only('id')),
            models.Prefetch('system_users', queryset=SystemUser.objects.all().only('id'))
        )

    def get_all_assets(self):
        args = [Q(granted_by_permissions=self)]
        pattern = set()
        nodes_keys = self.nodes.all().values_list('key', flat=True)
        for key in nodes_keys:
            pattern.add(r'^{0}$|^{0}:'.format(key))
        pattern = '|'.join(list(pattern))
        if pattern:
            args.append(Q(nodes__key__regex=pattern))
        args = reduce(lambda x, y: x | y, args)
        assets = Asset.objects.filter(args).distinct()
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
