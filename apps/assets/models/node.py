# -*- coding: utf-8 -*-
#
import uuid
import re
import time

from django.db import models, transaction
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from django.core.cache import cache

from common.utils import get_logger
from orgs.mixins.models import OrgModelMixin, OrgManager
from orgs.utils import set_current_org, get_current_org, tmp_to_org
from orgs.models import Organization


__all__ = ['Node']
logger = get_logger(__name__)


class NodeQuerySet(models.QuerySet):
    def delete(self):
        raise PermissionError("Bulk delete node deny")


class TreeMixin:
    tree_created_time = None
    tree_updated_time_cache_key = 'NODE_TREE_UPDATED_AT'
    tree_cache_time = 3600
    tree_assets_cache_key = 'NODE_TREE_ASSETS_UPDATED_AT'
    tree_assets_created_time = None
    _tree_service = None

    @classmethod
    def tree(cls):
        from ..utils import TreeService
        tree_updated_time = cache.get(cls.tree_updated_time_cache_key, 0)
        now = time.time()
        # 什么时候重新初始化 _tree_service
        if not cls.tree_created_time or \
                tree_updated_time > cls.tree_created_time:
            logger.debug("Create node tree")
            tree = TreeService.new()
            cls.tree_created_time = now
            cls.tree_assets_created_time = now
            cls._tree_service = tree
            return tree
        # 是否要重新初始化节点资产
        node_assets_updated_time = cache.get(cls.tree_assets_cache_key, 0)
        if not cls.tree_assets_created_time or \
                node_assets_updated_time > cls.tree_assets_created_time:
            cls._tree_service.init_assets()
            cls.tree_assets_created_time = now
            logger.debug("Refresh node tree assets")
        return cls._tree_service

    @classmethod
    def refresh_tree(cls, t=None):
        logger.debug("Refresh node tree")
        key = cls.tree_updated_time_cache_key
        ttl = cls.tree_cache_time
        if not t:
            t = time.time()
        cache.set(key, t, ttl)

    @classmethod
    def refresh_node_assets(cls, t=None):
        logger.debug("Refresh node tree assets")
        key = cls.tree_assets_cache_key
        ttl = cls.tree_cache_time
        if not t:
            t = time.time()
        cache.set(key, t, ttl)

    @property
    def _tree(self):
        return self.__class__.tree()

    @staticmethod
    def refresh_user_tree_cache():
        """
        当节点-节点关系，节点-资产关系发生变化时，应该刷新用户授权树缓存
        :return:
        """
        from perms.utils.asset_permission import AssetPermissionUtilV2
        AssetPermissionUtilV2.expire_all_user_tree_cache()


class FamilyMixin:
    __parents = None
    __children = None
    __all_children = None
    is_node = True

    @staticmethod
    def clean_children_keys(nodes_keys):
        nodes_keys = sorted(list(nodes_keys), key=lambda x: (len(x), x))
        nodes_keys_clean = []
        for key in nodes_keys[::-1]:
            found = False
            for k in nodes_keys:
                if key.startswith(k + ':'):
                    found = True
                    break
            if not found:
                nodes_keys_clean.append(key)
        return nodes_keys_clean

    @property
    def children(self):
        return self.get_children(with_self=False)

    @property
    def all_children(self):
        return self.get_all_children(with_self=False)

    def get_children_key_pattern(self, with_self=False):
        pattern = r'^{0}:[0-9]+$'.format(self.key)
        if with_self:
            pattern += r'|^{0}$'.format(self.key)
        return pattern

    def get_children(self, with_self=False):
        pattern = self.get_children_key_pattern(with_self=with_self)
        return Node.objects.filter(key__regex=pattern)

    def get_all_children_pattern(self, with_self=False):
        pattern = r'^{0}:'.format(self.key)
        if with_self:
            pattern += r'|^{0}$'.format(self.key)
        return pattern

    def get_all_children(self, with_self=False):
        pattern = self.get_all_children_pattern(with_self=with_self)
        children = Node.objects.filter(key__regex=pattern)
        return children

    @property
    def parents(self):
        return self.get_ancestor(with_self=False)

    def get_ancestor(self, with_self=False):
        ancestor_keys = self.get_ancestor_keys(with_self=with_self)
        return self.__class__.objects.filter(key__in=ancestor_keys)

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

    def get_family(self):
        ancestor = self.get_ancestor()
        children = self.get_all_children()
        return [*tuple(ancestor), self, *tuple(children)]

    @classmethod
    def get_nodes_ancestor_keys_by_key(cls, key, with_self=False):
        parent_keys = []
        key_list = key.split(":")
        if not with_self:
            key_list.pop()
        for i in range(len(key_list)):
            parent_keys.append(":".join(key_list))
            key_list.pop()
        return parent_keys

    def get_ancestor_keys(self, with_self=False):
        return self.__class__.get_nodes_ancestor_keys_by_key(
            self.key, with_self=with_self
        )

    def is_children(self, other):
        pattern = r'^{0}:[0-9]+$'.format(self.key)
        return re.match(pattern, other.key)

    def is_parent(self, other):
        return other.is_children(self)

    @property
    def parent_key(self):
        parent_key = ":".join(self.key.split(":")[:-1])
        return parent_key

    @property
    def parents_keys(self, with_self=False):
        keys = []
        key_list = self.key.split(":")
        if not with_self:
            key_list.pop()
        for i in range(len(key_list)):
            keys.append(':'.join(key_list))
            key_list.pop()
        return keys

    def get_next_child_key(self):
        mark = self.child_mark
        self.child_mark += 1
        self.save()
        return "{}:{}".format(self.key, mark)

    def get_next_child_preset_name(self):
        name = ugettext("New node")
        values = [
            child.value[child.value.rfind(' '):]
            for child in self.get_children()
            if child.value.startswith(name)
        ]
        values = [int(value) for value in values if value.strip().isdigit()]
        count = max(values) + 1 if values else 1
        return '{} {}'.format(name, count)

    def create_child(self, value, _id=None):
        with transaction.atomic():
            child_key = self.get_next_child_key()
            child = self.__class__.objects.create(
                id=_id, key=child_key, value=value
            )
            return child


class FullValueMixin:
    _full_value = None
    key = ''

    @property
    def full_value(self):
        if self.is_org_root():
            return self.value
        if self._full_value is not None:
            return self._full_value
        value = self._tree.get_node_full_tag(self.key)
        return value


class NodeAssetsMixin:
    _assets_amount = None
    key = ''
    id = None

    @property
    def assets_amount(self):
        """
        获取节点下所有资产数量速度太慢，所以需要重写，使用cache等方案
        :return:
        """
        if self._assets_amount is not None:
            return self._assets_amount
        amount = self._tree.assets_amount(self.key)
        return amount

    def get_all_assets(self):
        from .asset import Asset
        if self.is_org_root():
            return Asset.objects.filter(org_id=self.org_id)
        pattern = '^{0}$|^{0}:'.format(self.key)
        return Asset.objects.filter(nodes__key__regex=pattern).distinct()

    def get_assets(self):
        from .asset import Asset
        if self.is_org_root():
            assets = Asset.objects.filter(Q(nodes=self) | Q(nodes__isnull=True))
        else:
            assets = Asset.objects.filter(nodes=self)
        return assets.distinct()

    def get_valid_assets(self):
        return self.get_assets().valid()

    def get_all_valid_assets(self):
        return self.get_all_assets().valid()

    @classmethod
    def get_nodes_all_assets(cls, nodes_keys):
        from .asset import Asset
        nodes_keys = cls.clean_children_keys(nodes_keys)
        pattern = set()
        for key in nodes_keys:
            pattern.add(r'^{0}$|^{0}:'.format(key))
        pattern = '|'.join(list(pattern))
        return Asset.objects.filter(nodes__key__regex=pattern)


class SomeNodesMixin:
    key = ''
    default_key = '1'
    default_value = 'Default'
    ungrouped_key = '-10'
    ungrouped_value = _('ungrouped')
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
    def create_org_root_node(cls):
        # 如果使用current_org 在set_current_org时会死循环
        ori_org = get_current_org()
        with transaction.atomic():
            if not ori_org.is_real():
                return cls.default_node()
            set_current_org(Organization.root())
            org_nodes_roots = cls.objects.filter(key__regex=r'^[0-9]+$')
            org_nodes_roots_keys = org_nodes_roots.values_list('key', flat=True)
            if not org_nodes_roots_keys:
                org_nodes_roots_keys = ['1']
            key = max([int(k) for k in org_nodes_roots_keys])
            key = str(key + 1) if key != 0 else '2'
            set_current_org(ori_org)
            root = cls.objects.create(key=key, value=ori_org.name)
            return root

    @classmethod
    def org_root(cls):
        root = cls.objects.filter(key__regex=r'^[0-9]+$')
        if root:
            return root[0]
        else:
            return cls.create_org_root_node()

    @classmethod
    def ungrouped_node(cls):
        with tmp_to_org(Organization.system()):
            defaults = {'value': cls.ungrouped_key}
            obj, created = cls.objects.get_or_create(
                defaults=defaults, key=cls.ungrouped_key
            )
            return obj

    @classmethod
    def empty_node(cls):
        with tmp_to_org(Organization.system()):
            defaults = {'value': cls.empty_value}
            obj, created = cls.objects.get_or_create(
                defaults=defaults, key=cls.empty_key
            )
            return obj

    @classmethod
    def default_node(cls):
        with tmp_to_org(Organization.default()):
            defaults = {'value': cls.default_value}
            obj, created = cls.objects.get_or_create(
                defaults=defaults, key=cls.default_key,
            )
            return obj

    @classmethod
    def initial_some_nodes(cls):
        cls.default_node()
        cls.empty_node()
        cls.ungrouped_node()


class Node(OrgModelMixin, SomeNodesMixin, TreeMixin, FamilyMixin, FullValueMixin, NodeAssetsMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    key = models.CharField(unique=True, max_length=64, verbose_name=_("Key"))  # '1:1:1:1'
    value = models.CharField(max_length=128, verbose_name=_("Value"))
    child_mark = models.IntegerField(default=0)
    date_create = models.DateTimeField(auto_now_add=True)

    objects = OrgManager.from_queryset(NodeQuerySet)()
    is_node = True
    _parents = None

    class Meta:
        verbose_name = _("Node")
        ordering = ['key']

    def __str__(self):
        return self.value

    def __eq__(self, other):
        if not other:
            return False
        return self.id == other.id

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

    @property
    def level(self):
        return len(self.key.split(':'))

    @classmethod
    def refresh_nodes(cls):
        cls.refresh_tree()

    @classmethod
    def refresh_assets(cls):
        cls.refresh_node_assets()

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
                'node': {
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

    def delete(self, using=None, keep_parents=False):
        if self.children or self.get_assets():
            return
        return super().delete(using=using, keep_parents=keep_parents)

    @classmethod
    def generate_fake(cls, count=100):
        import random
        org = get_current_org()
        if not org or not org.is_real():
            Organization.default().change_to()
        i = 0
        while i < count:
            nodes = list(cls.objects.all())
            if count > 100:
                length = 100
            else:
                length = count

            for i in range(length):
                node = random.choice(nodes)
                node.create_child('Node {}'.format(i))
