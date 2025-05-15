#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
import json
import logging
from collections import defaultdict

from django.db import models
from django.db.models import Q, Count
from django.forms import model_to_dict
from django.utils.translation import gettext_lazy as _

from assets import const
from common.db.fields import EncryptMixin
from common.utils import lazyproperty
from labels.mixins import LabeledMixin
from orgs.mixins.models import OrgManager, JMSOrgBaseModel
from rbac.models import ContentType
from ..base import AbsConnectivity
from ..platform import Platform

__all__ = ['Asset', 'AssetQuerySet', 'default_node', 'Protocol']
logger = logging.getLogger(__name__)


def default_node():
    return []


class AssetManager(OrgManager):
    pass


class AssetQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def valid(self):
        return self.active()

    def gateways(self, is_gateway=1):
        kwargs = {'platform__name__startswith': 'Gateway'}
        if is_gateway:
            return self.filter(**kwargs)
        else:
            return self.exclude(**kwargs)

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
    _setting = None

    def __str__(self):
        return '{}/{}'.format(self.name, self.port)

    @lazyproperty
    def asset_platform_protocol(self):
        protocols = self.asset.platform.protocols.values('name', 'public', 'setting')
        protocols = list(filter(lambda p: p['name'] == self.name, protocols))
        return protocols[0] if len(protocols) > 0 else {}

    @property
    def setting(self):
        if self._setting is not None:
            return self._setting
        return self.asset_platform_protocol.get('setting', {})

    @setting.setter
    def setting(self, value):
        self._setting = value

    @property
    def public(self):
        return self.asset_platform_protocol.get('public', True)


class JSONFilterMixin:
    @staticmethod
    def get_json_filter_attr_q(name, value, match):
        """
        :param name: 属性名称
        :param value: 定义的结果
        :param match: 匹配方式
        :return:
        """
        from ..node import Node
        if not isinstance(value, (list, tuple)):
            value = [value]
        if name == 'nodes':
            nodes = Node.objects.filter(id__in=value)
            if match == 'm2m_all':
                assets = Asset.objects.all()
                for n in nodes:
                    children_pattern = Node.get_node_all_children_key_pattern(n.key)
                    assets = assets.filter(nodes__key__regex=children_pattern)
                q = Q(id__in=assets.values_list('id', flat=True))
                return q
            else:
                children = Node.get_nodes_all_children(nodes, with_self=True).values_list('id', flat=True)
                return Q(nodes__in=children)
        elif name == 'category':
            return Q(platform__category__in=value)
        elif name == 'type':
            return Q(platform__type__in=value)
        elif name == 'protocols':
            return Q(protocols__name__in=value)
        return None


class Asset(NodesRelationMixin, LabeledMixin, AbsConnectivity, JSONFilterMixin, JMSOrgBaseModel):
    Category = const.Category
    Type = const.AllTypes

    name = models.CharField(max_length=128, verbose_name=_('Name'))
    address = models.CharField(max_length=767, verbose_name=_('Address'), db_index=True)
    platform = models.ForeignKey(
        Platform, on_delete=models.PROTECT, verbose_name=_("Platform"), related_name='assets'
    )
    zone = models.ForeignKey(
        "assets.Zone", null=True, blank=True, related_name='assets',
        verbose_name=_("Zone"), on_delete=models.SET_NULL
    )
    nodes = models.ManyToManyField(
        'assets.Node', default=default_node, related_name='assets', verbose_name=_("Nodes")
    )
    directory_services = models.ManyToManyField(
        'assets.DirectoryService', related_name='assets',
        verbose_name=_("Directory service")
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Active'))
    gathered_info = models.JSONField(verbose_name=_('Gathered info'), default=dict, blank=True)  # 资产的一些信息，如 硬件信息
    custom_info = models.JSONField(verbose_name=_('Custom info'), default=dict)

    objects = AssetManager.from_queryset(AssetQuerySet)()

    def __str__(self):
        return '{0.name}({0.address})'.format(self)

    def get_labels(self):
        from labels.models import Label, LabeledResource
        res_type = ContentType.objects.get_for_model(self.__class__.label_model())
        label_ids = LabeledResource.objects.filter(res_type=res_type, res_id=self.id) \
            .values_list('label_id', flat=True)
        return Label.objects.filter(id__in=label_ids)

    @staticmethod
    def get_spec_values(instance, fields):
        info = {}
        for i in fields:
            v = getattr(instance, i.name)
            if isinstance(i, models.JSONField) and not isinstance(v, (list, dict)):
                v = json.loads(v)
            info[i.name] = v
        return info

    @lazyproperty
    def is_directory_service(self):
        return self.category == const.Category.DS and hasattr(self, 'ds')

    @lazyproperty
    def spec_info(self):
        instance = getattr(self, self.category, None)
        if not instance:
            return {}
        spec_fields = self.get_spec_fields(instance)
        return self.get_spec_values(instance, spec_fields)

    @staticmethod
    def get_spec_fields(instance, secret=False):
        spec_fields = [i for i in instance._meta.local_fields if i.name != 'asset_ptr']
        spec_fields = [i for i in spec_fields if isinstance(i, EncryptMixin) == secret]
        return spec_fields

    @lazyproperty
    def secret_info(self):
        instance = getattr(self, self.category, None)
        if not instance:
            return {}
        spec_fields = self.get_spec_fields(instance, secret=True)
        return self.get_spec_values(instance, spec_fields)

    @lazyproperty
    def info(self):
        info = {}
        info.update(self.gathered_info or {})
        info.update(self.custom_info or {})
        info.update(self.spec_info or {})
        return info

    @lazyproperty
    def auto_config(self):
        platform = self.platform
        auto_config = {
            'su_enabled': platform.su_enabled,
            'gateway_enabled': platform.gateway_enabled,
            'ansible_enabled': False
        }
        automation = getattr(self.platform, 'automation', None)
        if not automation:
            return auto_config
        auto_config.update(model_to_dict(automation))
        return auto_config

    @property
    def all_accounts(self):
        if not self.joined_dir_svcs:
            queryset = self.accounts.all()
        else:
            queryset = self.accounts.model.objects.filter(asset__in=[self.id, *self.joined_dir_svcs])
        return queryset

    @property
    def dc_accounts(self):
        queryset = self.accounts.model.objects.filter(asset__in=[*self.joined_dir_svcs])
        return queryset

    @lazyproperty
    def all_valid_accounts(self):
        queryset = (self.all_accounts.filter(is_active=True)
                    .prefetch_related('asset', 'asset__platform'))
        return queryset

    @lazyproperty
    def accounts_amount(self):
        return self.all_accounts.count()

    def get_target_ip(self):
        return self.address

    def get_target_ssh_port(self):
        return self.get_protocol_port('ssh')

    def get_protocol_port(self, protocol):
        protocol = self.protocols.all().filter(name=protocol).first()
        return protocol.port if protocol else 0

    def is_dir_svc(self):
        return self.category == const.Category.DS

    @property
    def joined_dir_svcs(self):
        return self.directory_services.all()

    @classmethod
    def compute_all_accounts_amount(cls, assets):
        from .ds import DirectoryService
        asset_ids = [asset.id for asset in assets]
        asset_id_dc_ids_mapper = defaultdict(list)
        dc_ids = set()

        asset_dc_relations = (
            Asset.directory_services.through.objects
            .filter(asset_id__in=asset_ids)
            .values_list('asset_id', 'directoryservice_id')
        )
        for asset_id, ds_id in asset_dc_relations:
            dc_ids.add(ds_id)
            asset_id_dc_ids_mapper[asset_id].append(ds_id)

        directory_services = (
            DirectoryService.objects.filter(id__in=dc_ids)
            .annotate(accounts_amount=Count('accounts'))
        )
        ds_accounts_amount_mapper = {ds.id: ds.accounts_amount for ds in directory_services}
        for asset in assets:
            asset_dc_ids = asset_id_dc_ids_mapper.get(asset.id, [])
            for dc_id in asset_dc_ids:
                ds_accounts = ds_accounts_amount_mapper.get(dc_id, 0)
                asset.accounts_amount += ds_accounts
        return assets

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
    def type(self):
        return self.platform.type

    @lazyproperty
    def category(self):
        return self.platform.category

    def is_category(self, category):
        return self.category == category

    def is_type(self, tp):
        return self.type == tp

    @property
    def is_gateway(self):
        return self.platform.name == const.GATEWAY_NAME

    @lazyproperty
    def gateway(self):
        if not self.zone_id:
            return
        if not self.platform.gateway_enabled:
            return
        return self.zone.select_gateway()

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

    @staticmethod
    def get_secret_type_assets(asset_ids, secret_type):
        assets = Asset.objects.filter(id__in=asset_ids)
        asset_protocol = assets.prefetch_related('protocols').values_list('id', 'protocols__name')
        protocol_secret_types_map = const.Protocol.protocol_secret_types()
        asset_secret_types_mapp = defaultdict(set)

        for asset_id, protocol in asset_protocol:
            secret_types = set(protocol_secret_types_map.get(protocol, []))
            asset_secret_types_mapp[asset_id].update(secret_types)

        return [
            asset for asset in assets
            if secret_type in asset_secret_types_mapp.get(asset.id, [])
        ]

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _("Asset")
        ordering = []
        permissions = [
            ('refresh_assethardwareinfo', _('Can refresh asset hardware info')),
            ('test_assetconnectivity', _('Can test asset connectivity')),
            ('match_asset', _('Can match asset')),
            ('change_assetnodes', _('Can change asset nodes')),
        ]
