#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import logging
import uuid
from functools import reduce
from collections import Iterable

from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from common.utils import lazyproperty
from orgs.mixins.models import OrgManager, JMSOrgBaseModel
from ..platform import Platform
from ..base import AbsConnectivity

__all__ = ['Asset', 'AssetQuerySet', 'default_node']
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


class NodesRelationMixin:
    NODES_CACHE_KEY = 'ASSET_NODES_{}'
    ALL_ASSET_NODES_CACHE_KEY = 'ALL_ASSETS_NODES'
    CACHE_TIME = 3600 * 24 * 7
    id = ""
    _all_nodes_keys = None

    def get_nodes(self):
        from assets.models import Node
        nodes = self.nodes.all()
        if not nodes:
            nodes = Node.objects.filter(id=Node.org_root().id)
        return nodes

    def get_all_nodes(self, flat=False):
        from ..node import Node
        node_keys = set()
        for node in self.get_nodes():
            ancestor_keys = node.get_ancestor_keys(with_self=True)
            node_keys.update(ancestor_keys)
        nodes = Node.objects.filter(key__in=node_keys).distinct()
        if flat:
            node_ids = set(nodes.values_list('id', flat=True))
            return node_ids
        else:
            return nodes


class Asset(AbsConnectivity, NodesRelationMixin, JMSOrgBaseModel):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    ip = models.CharField(max_length=128, verbose_name=_('IP'), db_index=True)
    protocols = models.ManyToManyField('Protocol', verbose_name=_("Protocols"), blank=True)
    platform = models.ForeignKey(Platform, default=Platform.default, on_delete=models.PROTECT,
                                 verbose_name=_("Platform"), related_name='assets')
    domain = models.ForeignKey("assets.Domain", null=True, blank=True, related_name='assets',
                               verbose_name=_("Domain"), on_delete=models.SET_NULL)
    nodes = models.ManyToManyField('assets.Node', default=default_node, related_name='assets',
                                   verbose_name=_("Nodes"))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))
    labels = models.ManyToManyField('assets.Label', blank=True, related_name='assets', verbose_name=_("Labels"))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))
    info = models.JSONField(verbose_name='Info', default=dict, blank=True)
    objects = AssetManager.from_queryset(AssetQuerySet)()

    def __str__(self):
        return '{0.name}({0.ip})'.format(self)

    def get_target_ip(self):
        return self.ip

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

    @property
    def protocols_as_list(self):
        return [{'name': p.name, 'port': p.port} for p in self.protocols.all()]

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
            'title': self.ip,
            'pId': parent_node.key,
            'isParent': False,
            'open': False,
            'iconSkin': icon_skin,
            'meta': {
                'type': 'asset',
                'data': {
                    'id': self.id,
                    'name': self.name,
                    'ip': self.ip,
                    'protocols': self.protocols,
                }
            }
        }
        tree_node = TreeNode(**data)
        return tree_node

    def filter_accounts(self, account_names=None):
        if account_names is None:
            return self.accounts.all()
        assert isinstance(account_names, Iterable), '`account_names` must be an iterable object'
        queries = Q(name__in=account_names) | Q(username__in=account_names)
        accounts = self.accounts.filter(queries)
        return accounts

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _("Asset")
        ordering = ["name", ]
        permissions = [
            ('refresh_assethardwareinfo', _('Can refresh asset hardware info')),
            ('test_assetconnectivity', _('Can test asset connectivity')),
            ('push_assetsystemuser', _('Can push system user to asset')),
            ('match_asset', _('Can match asset')),
            ('add_assettonode', _('Add asset to node')),
            ('move_assettonode', _('Move asset to node')),
        ]
