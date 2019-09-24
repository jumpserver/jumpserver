import uuid
from functools import reduce

from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from common.utils import date_expired_default
from orgs.mixins.models import OrgModelMixin
from assets.models import Asset, SystemUser, Node

from .base import BasePermission


__all__ = [
    'AssetPermission', 'Action',
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
    actions = models.IntegerField(choices=Action.DB_CHOICES, default=Action.ALL, verbose_name=_("Actions"))

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _("Asset permission")
        ordering = ('name',)

    @classmethod
    def get_queryset_with_prefetch(cls):
        return cls.objects.all().valid().prefetch_related(
            models.Prefetch('nodes', queryset=Node.objects.all().only('key')),
            models.Prefetch('assets', queryset=Asset.objects.all().only('id')),
            models.Prefetch('system_users', queryset=SystemUser.objects.all().only('id'))
        )

    def get_all_assets(self):
        from assets.models import Node
        nodes_keys = self.nodes.all().values_list('key', flat=True)
        assets_ids = set(self.assets.all().values_list('id', flat=True))
        nodes_assets_ids = Node.get_nodes_all_assets_ids(nodes_keys)
        assets_ids.update(nodes_assets_ids)
        assets = Asset.objects.filter(id__in=assets_ids)
        return assets
