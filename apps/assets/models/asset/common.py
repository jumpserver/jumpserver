#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import logging
from collections import defaultdict

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils import lazyproperty
from orgs.mixins.models import OrgManager, JMSOrgBaseModel
from ..base import AbsConnectivity
from ..platform import Platform

__all__ = ['Asset', 'AssetQuerySet', 'default_node', 'Protocol']
logger = logging.getLogger(__name__)


def default_node():
    try:
        from assets.models import Node
        root = Node.org_root()
        return Node.objects.filter(id=root.id)
    except:
        return None


class AssetManager(OrgManager):
    pass


class AssetQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def valid(self):
        return self.active()

    def has_protocol(self, name):
        return self.filter(protocols__contains=name)

    def group_by_platform(self) -> dict:
        groups = defaultdict(list)
        for asset in self.all():
            groups[asset.platform].append(asset)
        return groups


class NodesRelationMixin:
    NODES_CACHE_KEY = 'ASSET_NODES_{}'
    ALL_ASSET_NODES_CACHE_KEY = 'ALL_ASSETS_NODES'
    CACHE_TIME = 3600 * 24 * 7
    id: str
    _all_nodes_keys = None

    def get_nodes(self):
        from assets.models import Node
        nodes = self.nodes.all()
        if not nodes:
            nodes = Node.objects.filter(id=Node.org_root().id)
        return nodes

    def get_all_nodes(self, flat=False):
        from ..node import Node
        node_keys = self.get_all_node_keys()
        nodes = Node.objects.filter(key__in=node_keys).distinct()
        if not flat:
            return nodes
        node_ids = set(nodes.values_list('id', flat=True))
        return node_ids

    def get_all_node_keys(self):
        node_keys = set()
        for node in self.get_nodes():
            ancestor_keys = node.get_ancestor_keys(with_self=True)
            node_keys.update(ancestor_keys)
        return node_keys

    @classmethod
    def get_all_nodes_for_assets(cls, assets):
        from ..node import Node
        node_keys = set()
        for asset in assets:
            asset_node_keys = asset.get_all_node_keys()
            node_keys.update(asset_node_keys)
        nodes = Node.objects.filter(key__in=node_keys)
        return nodes


class Protocol(models.Model):
    name = models.CharField(max_length=32, verbose_name=_("Name"))
    port = models.IntegerField(verbose_name=_("Port"))
    asset = models.ForeignKey('Asset', on_delete=models.CASCADE, related_name='protocols', verbose_name=_("Asset"))

    def __str__(self):
        return '{}/{}'.format(self.name, self.port)


class Asset(NodesRelationMixin, AbsConnectivity, JMSOrgBaseModel):
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    address = models.CharField(max_length=128, verbose_name=_('IP'), db_index=True)
    platform = models.ForeignKey(Platform, on_delete=models.PROTECT, verbose_name=_("Platform"), related_name='assets')
    domain = models.ForeignKey("assets.Domain", null=True, blank=True, related_name='assets',
                               verbose_name=_("Domain"), on_delete=models.SET_NULL)
    nodes = models.ManyToManyField('assets.Node', default=default_node, related_name='assets',
                                   verbose_name=_("Nodes"))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))
    labels = models.ManyToManyField('assets.Label', blank=True, related_name='assets', verbose_name=_("Labels"))
    info = models.JSONField(verbose_name='Info', default=dict, blank=True)

    objects = AssetManager.from_queryset(AssetQuerySet)()

    def __str__(self):
        return '{0.name}({0.address})'.format(self)

    @property
    def specific(self):
        if not hasattr(self, self.category):
            return {}
        instance = getattr(self, self.category)
        private_fields = [i.name for i in instance._meta.local_fields if i.name != 'asset_ptr']
        return {i: getattr(instance, i) for i in private_fields}

    def get_target_ip(self):
        return self.address

    def get_target_ssh_port(self):
        protocol = self.protocols.all().filter(name='ssh').first()
        return protocol.port if protocol else 22

    @property
    def is_valid(self):
        warning = ''
        if not self.is_active:
            warning += ' inactive'
        if warning:
            return False, warning
        return True, warning

    def nodes_display(self):
        names = []
        for n in self.nodes.all():
            names.append(n.full_value)
        return names

    def labels_display(self):
        names = []
        for n in self.labels.all():
            names.append(n.name + ':' + n.value)
        return names

    @lazyproperty
    def primary_protocol(self):
        from assets.const.types import AllTypes
        primary_protocol_name = AllTypes.get_primary_protocol_name(self.category, self.type)
        protocol = self.protocols.get(name=primary_protocol_name)
        return protocol

    @lazyproperty
    def protocol(self):
        if not self.primary_protocol:
            return 'none'
        return self.primary_protocol.name

    @lazyproperty
    def port(self):
        if not self.primary_protocol:
            return 0
        return self.primary_protocol.port

    @lazyproperty
    def type(self):
        return self.platform.type

    @lazyproperty
    def category(self):
        return self.platform.category

    def as_node(self):
        from assets.models import Node
        fake_node = Node()
        fake_node.id = self.id
        fake_node.key = self.id
        fake_node.value = self.name
        fake_node.asset = self
        fake_node.is_node = False
        return fake_node

    def as_tree_node(self, parent_node):
        from common.tree import TreeNode
        icon_skin = 'file'
        platform_type = self.platform.type.lower()
        if platform_type == 'windows':
            icon_skin = 'windows'
        elif platform_type == 'linux':
            icon_skin = 'linux'
        data = {
            'id': str(self.id),
            'name': self.name,
            'title': self.address,
            'pId': parent_node.key,
            'isParent': False,
            'open': False,
            'iconSkin': icon_skin,
            'meta': {
                'type': 'asset',
                'data': {
                    'id': self.id,
                    'name': self.name,
                    'address': self.address,
                    'protocols': self.protocols,
                }
            }
        }
        tree_node = TreeNode(**data)
        return tree_node

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _("Asset")
        ordering = ["name", ]
        permissions = [
            ('refresh_assethardwareinfo', _('Can refresh asset hardware info')),
            ('test_assetconnectivity', _('Can test asset connectivity')),
            ('push_assetaccount', _('Can push account to asset')),
            ('match_asset', _('Can match asset')),
            ('add_assettonode', _('Add asset to node')),
            ('move_assettonode', _('Move asset to node')),
        ]
