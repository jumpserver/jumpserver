#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import uuid
import logging
from functools import reduce

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils import lazyproperty
from orgs.mixins.models import OrgModelMixin, OrgManager
from assets.const import Category, AllTypes
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


class Asset(AbsConnectivity, NodesRelationMixin, OrgModelMixin):
    Category = Category
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    hostname = models.CharField(max_length=128, verbose_name=_('Hostname'))
    ip = models.CharField(max_length=128, verbose_name=_('IP'), db_index=True)
    category = models.CharField(max_length=16, choices=Category.choices, verbose_name=_("Category"))
    type = models.CharField(max_length=128, choices=AllTypes.choices, verbose_name=_("Type"))
    _protocols = models.CharField(max_length=128, default='ssh/22', blank=True, verbose_name=_("Protocols"))
    protocols = models.ManyToManyField('Protocol', verbose_name=_("Protocols"), blank=True)
    platform = models.ForeignKey(Platform, default=Platform.default, on_delete=models.PROTECT,
                                 verbose_name=_("Platform"), related_name='assets')
    domain = models.ForeignKey("assets.Domain", null=True, blank=True, related_name='assets',
                               verbose_name=_("Domain"), on_delete=models.SET_NULL)
    nodes = models.ManyToManyField('assets.Node', default=default_node, related_name='assets',
                                   verbose_name=_("Nodes"))
    is_active = models.BooleanField(default=True, verbose_name=_('Is active'))

    # Auth
    admin_user = models.ForeignKey('assets.SystemUser', on_delete=models.SET_NULL, null=True,
                                   verbose_name=_("Admin user"), related_name='admin_assets')
    # Some information
    public_ip = models.CharField(max_length=128, blank=True, null=True, verbose_name=_('Public IP'))
    number = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('Asset number'))

    labels = models.ManyToManyField('assets.Label', blank=True, related_name='assets', verbose_name=_("Labels"))
    created_by = models.CharField(max_length=128, null=True, blank=True, verbose_name=_('Created by'))
    date_created = models.DateTimeField(auto_now_add=True, null=True, blank=True, verbose_name=_('Date created'))
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    objects = AssetManager.from_queryset(AssetQuerySet)()

    def __str__(self):
        return '{0.hostname}({0.ip})'.format(self)

    def get_target_ip(self):
        return self.ip

    @property
    def admin_user_display(self):
        if not self.admin_user:
            return ''
        return str(self.admin_user)

    @property
    def is_valid(self):
        warning = ''
        if not self.is_active:
            warning += ' inactive'
        if warning:
            return False, warning
        return True, warning

    @lazyproperty
    def platform_base(self):
        return self.platform.type

    @lazyproperty
    def admin_user_username(self):
        """求可连接性时，直接用用户名去取，避免再查一次admin user
        serializer 中直接通过annotate方式返回了这个
        """
        return self.admin_user.username

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

    def as_node(self):
        from assets.models import Node
        fake_node = Node()
        fake_node.id = self.id
        fake_node.key = self.id
        fake_node.value = self.hostname
        fake_node.asset = self
        fake_node.is_node = False
        return fake_node

    def as_tree_node(self, parent_node):
        from common.tree import TreeNode
        icon_skin = 'file'
        if self.platform_base.lower() == 'windows':
            icon_skin = 'windows'
        elif self.platform_base.lower() == 'linux':
            icon_skin = 'linux'
        data = {
            'id': str(self.id),
            'name': self.hostname,
            'title': self.ip,
            'pId': parent_node.key,
            'isParent': False,
            'open': False,
            'iconSkin': icon_skin,
            'meta': {
                'type': 'asset',
                'data': {
                    'id': self.id,
                    'hostname': self.hostname,
                    'ip': self.ip,
                    'protocols': self.protocols,
                    'platform': self.platform_base,
                }
            }
        }
        tree_node = TreeNode(**data)
        return tree_node

    def get_all_system_users(self):
        from assets.models import SystemUser
        system_user_ids = SystemUser.assets.through.objects.filter(asset=self) \
            .values_list('systemuser_id', flat=True)
        system_users = SystemUser.objects.filter(id__in=system_user_ids)
        return system_users

    def save(self, *args, **kwargs):
        self.type = self.platform.type
        self.category = self.platform.category
        return super().save(*args, **kwargs)

    # TODO 暂时为了接口文档添加
    @property
    def os(self):
        return

    class Meta:
        unique_together = [('org_id', 'hostname')]
        verbose_name = _("Asset")
        ordering = ["hostname", ]
        permissions = [
            ('refresh_assethardwareinfo', _('Can refresh asset hardware info')),
            ('test_assetconnectivity', _('Can test asset connectivity')),
            ('push_assetsystemuser', _('Can push system user to asset')),
            ('match_asset', _('Can match asset')),
            ('add_assettonode', _('Add asset to node')),
            ('move_assettonode', _('Move asset to node')),
        ]
