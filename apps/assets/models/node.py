# -*- coding: utf-8 -*-
#
import re
import threading
import time
import uuid
from collections import defaultdict

from django.core.cache import cache
from django.db import models, transaction
from django.db.models import Q, Manager
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _, gettext

from common.db.models import output_as_string
from common.utils import get_logger, timeit
from common.utils.lock import DistributedLock
from orgs.mixins.models import OrgManager, JMSOrgBaseModel
from orgs.models import Organization
from orgs.utils import get_current_org, tmp_to_org, tmp_to_root_org

__all__ = ['Node', 'FamilyMixin', 'compute_parent_key', 'NodeQuerySet']
logger = get_logger(__name__)


def compute_parent_key(key):
    try:
        return key[:key.rindex(':')]
    except ValueError:
        return ''


class NodeQuerySet(models.QuerySet):
    pass


class FamilyMixin:
    __parents = None
    __children = None
    __all_children = None
    is_node = True
    child_mark: int

    @staticmethod
    def clean_children_keys(nodes_keys):
        sort_key = lambda k: [int(i) for i in k.split(':')]
        nodes_keys = sorted(list(nodes_keys), key=sort_key)

        nodes_keys_clean = []
        base_key = ''
        for key in nodes_keys:
            if key.startswith(base_key + ':'):
                continue
            nodes_keys_clean.append(key)
            base_key = key
        return nodes_keys_clean

    @classmethod
    def get_node_all_children_key_pattern(cls, key, with_self=True):
        pattern = r'^{0}:'.format(key)
        if with_self:
            pattern += r'|^{0}$'.format(key)
        return pattern

    @classmethod
    def get_nodes_children_key_pattern(cls, nodes, with_self=True):
        keys = [i.key for i in nodes]
        keys = cls.clean_children_keys(keys)
        patterns = [cls.get_node_all_children_key_pattern(key) for key in keys]
        patterns = '|'.join(patterns)
        return patterns

    @classmethod
    def get_nodes_all_children(cls, nodes, with_self=True):
        pattern = cls.get_nodes_children_key_pattern(nodes, with_self=with_self)
        if not pattern:
            # 如果 pattern = ''
            # key__iregex 报错 (1139, "Got error 'empty (sub)expression' from regexp")
            return cls.objects.none()
        return Node.objects.filter(key__iregex=pattern)

    @classmethod
    def get_node_children_key_pattern(cls, key, with_self=True):
        pattern = r'^{0}:[0-9]+$'.format(key)
        if with_self:
            pattern += r'|^{0}$'.format(key)
        return pattern

    def get_children_key_pattern(self, with_self=False):
        return self.get_node_children_key_pattern(self.key, with_self=with_self)

    def get_all_children_pattern(self, with_self=False):
        return self.get_node_all_children_key_pattern(self.key, with_self=with_self)

    def is_children(self, other):
        children_pattern = other.get_children_key_pattern(with_self=False)
        return re.match(children_pattern, self.key)

    def get_children(self, with_self=False):
        q = Q(parent_key=self.key)
        if with_self:
            q |= Q(key=self.key)
        return Node.objects.filter(q)

    def get_all_children(self, with_self=False):
        q = Q(key__istartswith=f'{self.key}:')
        if with_self:
            q |= Q(key=self.key)
        return Node.objects.filter(q)

    @classmethod
    def get_ancestor_queryset(cls, queryset, with_self=True):
        parent_keys = set()
        for i in queryset:
            parent_keys.update(set(i.get_ancestor_keys(with_self=with_self)))
        queryset = queryset.model.objects.filter(key__in=list(parent_keys)).distinct()
        return queryset

    @property
    def children(self):
        return self.get_children(with_self=False)

    @property
    def all_children(self):
        return self.get_all_children(with_self=False)

    def create_child(self, value=None, _id=None):
        with atomic(savepoint=False):
            child_key = self.get_next_child_key()
            if value is None:
                value = child_key
            child = self.__class__.objects.create(
                id=_id, key=child_key, value=value
            )
            return child

    def get_or_create_child(self, value, _id=None):
        """
        :return: Node, bool (created)
        """
        children = self.get_children()
        exist = children.filter(value=value).exists()
        if exist:
            child = children.filter(value=value).first()
            created = False
        else:
            child = self.create_child(value, _id)
            created = True
        return child, created

    def get_valid_child_mark(self):
        key = "{}:{}".format(self.key, self.child_mark)
        if not self.__class__.objects.filter(key=key).exists():
            return self.child_mark
        children_keys = self.get_children().values_list('key', flat=True)
        children_keys_last = [key.split(':')[-1] for key in children_keys]
        children_keys_last = [int(k) for k in children_keys_last if k.strip().isdigit()]
        max_key_last = max(children_keys_last) if children_keys_last else 1
        return max_key_last + 1

    def get_next_child_key(self):
        child_mark = self.get_valid_child_mark()
        key = "{}:{}".format(self.key, child_mark)
        self.child_mark = child_mark + 1
        self.save()
        return key

    def get_next_child_preset_name(self):
        name = gettext("New node")
        values = [
            child.value[child.value.rfind(' '):]
            for child in self.get_children()
            if child.value.startswith(name)
        ]
        values = [int(value) for value in values if value.strip().isdigit()]
        count = max(values) + 1 if values else 1
        return '{} {}'.format(name, count)

    # Parents
    @classmethod
    def get_node_ancestor_keys(cls, key, with_self=False):
        parent_keys = []
        key_list = key.split(":")
        if not with_self:
            key_list.pop()
        for i in range(len(key_list)):
            parent_keys.append(":".join(key_list))
            key_list.pop()
        return parent_keys

    def get_ancestor_keys(self, with_self=False):
        return self.get_node_ancestor_keys(self.key, with_self=with_self)

    @property
    def ancestors(self):
        return self.get_ancestors(with_self=False)

    def get_ancestors(self, with_self=False):
        ancestor_keys = self.get_ancestor_keys(with_self=with_self)
        return self.__class__.objects.filter(key__in=ancestor_keys)

    def compute_parent_key(self):
        return compute_parent_key(self.key)

    def is_parent(self, other):
        return other.is_children(self)

    @property
    def parent(self):
        if self.is_org_root():
            return self
        parent_key = self.parent_key
        return Node.objects.get(key=parent_key)

    @parent.setter
    def parent(self, parent):
        if not self.is_node:
            self.key = parent.key + ':fake'
            return
        children = self.get_all_children()
        old_key = self.key
        with transaction.atomic():
            self.key = parent.get_next_child_key()
            self.save()
            for child in children:
                child.key = child.key.replace(old_key, self.key, 1)
                child.save()

    def get_siblings(self, with_self=False):
        key = ':'.join(self.key.split(':')[:-1])
        pattern = r'^{}:[0-9]+$'.format(key)
        sibling = Node.objects.filter(
            key__regex=pattern.format(self.key)
        )
        if not with_self:
            sibling = sibling.exclude(key=self.key)
        return sibling

    @classmethod
    def create_node_by_full_value(cls, full_value):
        if not full_value:
            return []
        nodes_family = full_value.split('/')
        nodes_family = [v for v in nodes_family if v]
        org_root = cls.org_root()
        if nodes_family[0] == org_root.value:
            nodes_family = nodes_family[1:]
        return cls.create_nodes_recurse(nodes_family, org_root)

    @classmethod
    def create_nodes_recurse(cls, values, parent=None):
        values = [v for v in values if v]
        if not values:
            return None
        if parent is None:
            parent = cls.org_root()
        value = values[0]
        child, created = parent.get_or_create_child(value=value)
        if len(values) == 1:
            return child
        return cls.create_nodes_recurse(values[1:], child)

    def get_family(self):
        ancestors = self.get_ancestors()
        children = self.get_all_children()
        return [*tuple(ancestors), self, *tuple(children)]


class NodeAllAssetsMappingMixin:
    # { org_id: { node_key: [ asset1_id, asset2_id ] } }
    orgid_nodekey_assetsid_mapping = defaultdict(dict)
    locks_for_get_mapping_from_cache = defaultdict(threading.Lock)

    @classmethod
    def get_lock(cls, org_id):
        lock = cls.locks_for_get_mapping_from_cache[str(org_id)]
        return lock

    @classmethod
    def get_node_all_asset_ids_mapping(cls, org_id):
        _mapping = cls.get_node_all_asset_ids_mapping_from_memory(org_id)
        if _mapping:
            return _mapping

        with cls.get_lock(org_id):
            _mapping = cls.get_node_all_asset_ids_mapping_from_cache_or_generate_to_cache(org_id)
            cls.set_node_all_asset_ids_mapping_to_memory(org_id, mapping=_mapping)
        return _mapping

    # from memory
    @classmethod
    def get_node_all_asset_ids_mapping_from_memory(cls, org_id):
        mapping = cls.orgid_nodekey_assetsid_mapping.get(org_id, {})
        return mapping

    @classmethod
    def set_node_all_asset_ids_mapping_to_memory(cls, org_id, mapping):
        cls.orgid_nodekey_assetsid_mapping[org_id] = mapping

    @classmethod
    def expire_node_all_asset_ids_memory_mapping(cls, org_id):
        org_id = str(org_id)
        cls.orgid_nodekey_assetsid_mapping.pop(org_id, None)

    @classmethod
    def expire_all_orgs_node_all_asset_ids_memory_mapping(cls):
        orgs = Organization.objects.all()
        org_ids = [str(org.id) for org in orgs]
        org_ids.append(Organization.ROOT_ID)

        for i in org_ids:
            cls.expire_node_all_asset_ids_memory_mapping(i)

    # get order: from memory -> (from cache -> to generate)
    @classmethod
    def get_node_all_asset_ids_mapping_from_cache_or_generate_to_cache(cls, org_id):
        mapping = cls.get_node_all_asset_ids_mapping_from_cache(org_id)
        if mapping:
            return mapping

        lock_key = f'KEY_LOCK_GENERATE_ORG_{org_id}_NODE_ALL_ASSET_ids_MAPPING'
        with DistributedLock(lock_key):
            # 这里使用无限期锁，原因是如果这里卡住了，就卡在数据库了，说明
            # 数据库繁忙，所以不应该再有线程执行这个操作，使数据库忙上加忙

            _mapping = cls.get_node_all_asset_ids_mapping_from_cache(org_id)
            if _mapping:
                return _mapping

            _mapping = cls.generate_node_all_asset_ids_mapping(org_id)
            cache_key = cls._get_cache_key_for_node_all_asset_ids_mapping(org_id)
            cache.set(cache_key, mapping, timeout=None)
            return _mapping

    @classmethod
    def get_node_all_asset_ids_mapping_from_cache(cls, org_id):
        cache_key = cls._get_cache_key_for_node_all_asset_ids_mapping(org_id)
        mapping = cache.get(cache_key)
        return mapping

    @classmethod
    def expire_node_all_asset_ids_cache_mapping(cls, org_id):
        cache_key = cls._get_cache_key_for_node_all_asset_ids_mapping(org_id)
        cache.delete(cache_key)

    @staticmethod
    def _get_cache_key_for_node_all_asset_ids_mapping(org_id):
        return 'ASSETS_ORG_NODE_ALL_ASSET_ids_MAPPING_{}'.format(org_id)

    @classmethod
    @timeit
    def generate_node_all_asset_ids_mapping(cls, org_id):
        logger.info(f'Generate node asset mapping: org_id={org_id}')
        t1 = time.time()
        with tmp_to_org(org_id):
            node_ids_key = Node.objects.annotate(
                char_id=output_as_string('id')
            ).values_list('char_id', 'key')

            node_id_ancestor_keys_mapping = {
                node_id: cls.get_node_ancestor_keys(node_key, with_self=True)
                for node_id, node_key in node_ids_key
            }

            # * 直接取出全部. filter(node__org_id=org_id)(大规模下会更慢)
            nodes_asset_ids = cls.assets.through.objects.all() \
                .annotate(char_node_id=output_as_string('node_id')) \
                .annotate(char_asset_id=output_as_string('asset_id')) \
                .values_list('char_node_id', 'char_asset_id')

            nodeid_assetsid_mapping = defaultdict(set)
            for node_id, asset_id in nodes_asset_ids:
                nodeid_assetsid_mapping[node_id].add(asset_id)

        t2 = time.time()

        mapping = defaultdict(set)
        for node_id, node_key in node_ids_key:
            asset_ids = nodeid_assetsid_mapping[node_id]
            node_ancestor_keys = node_id_ancestor_keys_mapping[node_id]
            for ancestor_key in node_ancestor_keys:
                mapping[ancestor_key].update(asset_ids)

        t3 = time.time()
        logger.info('Generate asset nodes mapping, DB query: {:.2f}s, mapping: {:.2f}s'.format(t2 - t1, t3 - t2))
        return mapping


class NodeAssetsMixin(NodeAllAssetsMappingMixin):
    org_id: str
    key = ''
    id = None
    objects: Manager

    def get_all_assets(self):
        from .asset import Asset
        q = Q(nodes__key__startswith=f'{self.key}:') | Q(nodes__key=self.key)
        return Asset.objects.filter(q).distinct()

    def get_assets_amount(self):
        return self.get_all_assets().count()

    @classmethod
    def get_node_all_assets_by_key_v2(cls, key):
        # 最初的写法是：
        #   Asset.objects.filter(Q(nodes__key__startswith=f'{node.key}:') | Q(nodes__id=node.id))
        #   可是 startswith 会导致表关联时 Asset 索引失效
        from .asset import Asset
        node_ids = cls.objects.filter(
            Q(key__startswith=f'{key}:') | Q(key=key)
        ).values_list('id', flat=True).distinct()
        assets = Asset.objects.filter(
            nodes__id__in=list(node_ids)
        ).distinct()
        return assets

    def get_assets(self):
        from .asset import Asset
        assets = Asset.objects.filter(nodes=self)
        return assets.distinct()

    def get_valid_assets(self):
        return self.get_assets().valid()

    def get_all_valid_assets(self):
        return self.get_all_assets().valid()

    @classmethod
    def get_nodes_all_asset_ids_by_keys(cls, nodes_keys):
        nodes = Node.objects.filter(key__in=nodes_keys)
        asset_ids = cls.get_nodes_all_assets(*nodes).values_list('id', flat=True)
        return asset_ids

    @classmethod
    @timeit
    def get_nodes_all_assets(cls, *nodes, distinct=True):
        from .asset import Asset
        node_ids = set()
        descendant_node_query = Q()
        for n in nodes:
            node_ids.add(n.id)
            descendant_node_query |= Q(key__istartswith=f'{n.key}:')
        if descendant_node_query:
            _ids = Node.objects.order_by().filter(descendant_node_query).values_list('id', flat=True)
            node_ids.update(_ids)
        assets = Asset.objects.order_by().filter(nodes__id__in=node_ids)
        if distinct:
            assets = assets.distinct()
        return assets

    def get_all_asset_ids(self):
        asset_ids = self.get_all_asset_ids_by_node_key(org_id=self.org_id, node_key=self.key)
        return set(asset_ids)

    @classmethod
    def get_all_asset_ids_by_node_key(cls, org_id, node_key):
        org_id = str(org_id)
        nodekey_assetsid_mapping = cls.get_node_all_asset_ids_mapping(org_id)
        asset_ids = nodekey_assetsid_mapping.get(node_key, [])
        return set(asset_ids)


class SomeNodesMixin:
    key = ''
    default_key = '1'
    empty_key = '-11'
    empty_value = _("empty")

    def is_default_node(self):
        return self.key == self.default_key

    def is_org_root(self):
        if self.key.isdigit():
            return True
        else:
            return False

    @classmethod
    def org_root(cls):
        # 如果使用current_org 在set_current_org时会死循环
        ori_org = get_current_org()

        if ori_org and ori_org.is_default():
            return cls.default_node()

        if ori_org and ori_org.is_root():
            return cls.default_node()

        org_roots = cls.org_root_nodes()
        org_roots_length = len(org_roots)

        if org_roots_length == 1:
            root = org_roots[0]
            return root
        elif org_roots_length == 0:
            root = cls.create_org_root_node()
            return root
        else:
            error = 'Current org {} root node not 1, get {}'.format(ori_org, org_roots_length)
            raise ValueError(error)

    @classmethod
    def default_node(cls):
        default_org = Organization.default()
        with tmp_to_org(default_org):
            defaults = {'value': default_org.name}
            obj, created = cls.objects.get_or_create(defaults=defaults, key=cls.default_key)
            return obj

    @classmethod
    def create_org_root_node(cls):
        ori_org = get_current_org()
        with transaction.atomic():
            key = cls.get_next_org_root_node_key()
            root = cls.objects.create(key=key, value=ori_org.name)
            return root

    @classmethod
    def get_next_org_root_node_key(cls):
        with tmp_to_root_org():
            org_nodes_roots = cls.org_root_nodes()
            org_nodes_roots_keys = org_nodes_roots.values_list('key', flat=True)
            if not org_nodes_roots_keys:
                org_nodes_roots_keys = ['1']
            max_key = max([int(k) for k in org_nodes_roots_keys])
            key = str(max_key + 1) if max_key > 0 else '2'
            return key

    @classmethod
    def org_root_nodes(cls):
        root_nodes = cls.objects.filter(parent_key='', key__regex=r'^[0-9]+$') \
            .exclude(key__startswith='-').order_by('key')
        return root_nodes


class Node(JMSOrgBaseModel, SomeNodesMixin, FamilyMixin, NodeAssetsMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    key = models.CharField(unique=True, max_length=64, verbose_name=_("Key"))  # '1:1:1:1'
    value = models.CharField(max_length=128, verbose_name=_("Value"))
    full_value = models.CharField(max_length=4096, verbose_name=_('Full value'), default='')
    child_mark = models.IntegerField(default=0)
    date_create = models.DateTimeField(auto_now_add=True)
    parent_key = models.CharField(
        max_length=64, verbose_name=_("Parent key"), db_index=True, default=''
    )
    assets_amount = models.IntegerField(default=0)

    objects = OrgManager.from_queryset(NodeQuerySet)()
    is_node = True
    _parents = None

    class Meta:
        verbose_name = _("Node")
        ordering = ['parent_key', 'value']
        permissions = [
            ('match_node', _('Can match node')),
        ]

    def __str__(self):
        return self.full_value

    def __gt__(self, other):
        self_key = [int(k) for k in self.key.split(':')]
        other_key = [int(k) for k in other.key.split(':')]
        self_parent_key = self_key[:-1]
        other_parent_key = other_key[:-1]

        if self_parent_key and self_parent_key == other_parent_key:
            return self.value > other.value
        return self_key > other_key

    def __lt__(self, other):
        return not self.__gt__(other)

    @property
    def name(self):
        return self.value

    def computed_full_value(self):
        # 不要在列表中调用该属性
        values = self.__class__.objects.filter(
            key__in=self.get_ancestor_keys()
        ).values_list('key', 'value')
        values = [v for k, v in sorted(values, key=lambda x: len(x[0]))]
        values.append(str(self.value))
        return '/' + '/'.join(values)

    @property
    def level(self):
        return len(self.key.split(':'))

    def as_tree_node(self):
        from common.tree import TreeNode
        name = '{} ({})'.format(self.value, self.assets_amount)
        data = {
            'id': self.key,
            'name': name,
            'title': name,
            'pId': self.parent_key,
            'isParent': True,
            'open': self.is_org_root(),
            'meta': {
                'data': {
                    "id": self.id,
                    "name": self.name,
                    "value": self.value,
                    "key": self.key,
                    "assets_amount": self.assets_amount,
                },
                'type': 'node'
            }
        }
        tree_node = TreeNode(**data)
        return tree_node

    def has_offspring_assets(self):
        # 拥有后代资产
        return self.get_all_assets().exists()

    def delete(self, using=None, keep_parents=False):
        if self.has_offspring_assets():
            return
        self.all_children.delete()
        return super().delete(using=using, keep_parents=keep_parents)

    def update_child_full_value(self):
        nodes = self.get_all_children(with_self=True)
        sort_key_func = lambda n: [int(i) for i in n.key.split(':')]
        nodes_sorted = sorted(list(nodes), key=sort_key_func)
        nodes_mapper = {n.key: n for n in nodes_sorted}
        if not self.is_org_root():
            # 如果是org_root，那么parent_key为'', parent为自己，所以这种情况不处理
            # 更新自己时，自己的parent_key获取不到
            nodes_mapper.update({self.parent_key: self.parent})
        for node in nodes_sorted:
            parent = nodes_mapper.get(node.parent_key)
            if not parent:
                if node.parent_key:
                    logger.error(f'Node parent node in mapper: {node.parent_key} {node.value}')
                continue
            node.full_value = parent.full_value + '/' + node.value
        self.__class__.objects.bulk_update(nodes, ['full_value'])

    def save(self, *args, **kwargs):
        self.full_value = self.computed_full_value()
        instance = super().save(*args, **kwargs)
        self.update_child_full_value()
        return instance
