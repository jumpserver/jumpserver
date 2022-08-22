#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import logging
import uuid
from functools import reduce

from django.db import models
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.models import OrgManager, JMSOrgBaseModel
from ...const import Category
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
        nodes = []
        for node in self.get_nodes():
            _nodes = node.get_ancestors(with_self=True)
            nodes.append(_nodes)
        if flat:
            nodes = list(reduce(lambda x, y: set(x) | set(y), nodes))
        return nodes


class Asset(AbsConnectivity, NodesRelationMixin, JMSOrgBaseModel):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_('Hostname'))
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

    objects = AssetManager.from_queryset(AssetQuerySet)()

    def __str__(self):
        return '{0.name}({0.ip})'.format(self)

    def get_target_ip(self):
        return self.ip

    @property
    def is_valid(self):
        warning = ''
        if not self.is_active:
            warning += ' inactive'
        if warning:
            return False, warning
        return True, warning

    def domain_display(self):
        if self.domain:
            return self.domain.name
        return ''

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
    def type(self):
        return self.platform.type

    @property
    def type_display(self):
        value = self.platform.type
        return Category.get_label(value)

    @property
    def category(self):
        return self.platform.category

    @property
    def category_display(self):
        value = self.platform.category
        return Category.get_label(value)

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
