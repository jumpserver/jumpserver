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

from orgs.mixins.models import OrgModelMixin, OrgManager
from orgs.utils import set_current_org, get_current_org
from orgs.models import Organization


__all__ = ['Node']


class NodeQuerySet(models.QuerySet):
    def delete(self):
        raise PermissionError("Bulk delete node deny")


class TreeMixin:
    time_tree_updated = None
    time_tree_updated_cache_key = 'NODE_TREE_CREATED_AT'
    tree_cache_time = 3600
    _tree_service = None

    @classmethod
    def tree(cls):
        # Todo: 有待优化, 因为每次刷新都会导致其他节点的tree失效
        # Todo: ungroup node
        # TOdo: 游离的资产，在树上显示的数量不对
        # Todo: api key页面有bug
        from ..utils import TreeService
        cache_updated_time = cls.get_cache_time()
        if not cls.time_tree_updated or \
                cache_updated_time != cls.time_tree_updated:
            t = TreeService.new()
            cls.update_cache_tree(t)
            return t
        return cls._tree_service

    @classmethod
    def get_cache_time(cls):
        return cache.get(cls.time_tree_updated_cache_key)

    @classmethod
    def update_cache_tree(cls, t):
        cls._tree_service = t
        now = time.time()
        cls.time_tree_updated = now
        cache.set(cls.time_tree_updated_cache_key, now, cls.tree_cache_time)

    @classmethod
    def expire_cache_tree(cls):
        cache.delete(cls.time_tree_updated_cache_key)

    @classmethod
    def refresh_tree(cls):
        cls.expire_cache_tree()

    @property
    def _tree(self):
        return self.__class__.tree()


class FamilyMixin:
    __parents = None
    __children = None
    __all_children = None
    is_node = True

    @property
    def children(self):
        return self.get_children(with_self=False)

    @property
    def all_children(self):
        return self.get_all_children(with_self=False)

    def get_children(self, with_self=False):
        pattern = r'^{0}:[0-9]+$'.format(self.key)
        if with_self:
            pattern += r'|^{0}$'.format(self.key)
        return Node.objects.filter(key__regex=pattern)

    def get_all_children(self, with_self=False):
        pattern = r'^{0}:'.format(self.key)
        if with_self:
            pattern += r'|^{0}$'.format(self.key)
        children = Node.objects.filter(key__regex=pattern)
        return children

    @property
    def parents(self):
        return self.get_ancestor(with_self=False)

    def get_ancestor(self, with_self=False):
        parents = self.parents
        if with_self:
            parents = list(parents)
            parents.append(self)
        return parents

    @property
    def parent(self):
        if self.is_root():
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
            for child in children:
                child.key = child.key.replace(old_key, self.key, 1)
                child.save()
            self.save()

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

    def get_ancestor_keys(self, with_self=False):
        parent_keys = []
        key_list = self.key.split(":")
        if not with_self:
            key_list.pop()
        for i in range(len(key_list)):
            parent_keys.append(":".join(key_list))
            key_list.pop()
        return parent_keys

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


class FullValueMixin:
    _full_value = None
    key = ''

    @property
    def full_value(self):
        if self.is_root():
            return self.value
        if self._full_value is not None:
            return self._full_value
        print("Get full value")
        value = self._tree.get_node_full_tag(self.key)
        return value


class NodeAssetsMixin:
    _assets_amount_cache_key = '_NODE_ASSETS_AMOUNT_{}'
    _assets_cache_key = '_NODE_ASSETS_{}'
    _assets_amount = None
    key = ''
    cache_time = 3600 * 24 * 7
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

    # TOdo: 是否依赖tree
    def get_all_assets(self):
        from .asset import Asset
        if self.is_root():
            return Asset.objects.filter(org_id=self.org_id)
        assets_ids = self._tree.all_assets(self.key)
        return Asset.objects.filter(id__in=assets_ids)

    def assets_ids(self):
        assets_ids = self._tree.assets(self.key)
        return assets_ids

    def get_assets(self):
        from .asset import Asset
        if self.is_default_node():
            assets = Asset.objects.filter(Q(nodes__id=self.id) | Q(nodes__isnull=True))
        else:
            assets = Asset.objects.filter(id=self.assets_ids())
        return assets.distinct()

    def get_valid_assets(self):
        return self.get_assets().valid()

    def get_all_valid_assets(self):
        return self.get_all_assets().valid()


class Node(OrgModelMixin, TreeMixin, FamilyMixin, FullValueMixin, NodeAssetsMixin):
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
        # if self.is_root() and not other.is_root():
        #     return False
        # elif not self.is_root() and other.is_root():
        #     return True
        self_key = [int(k) for k in self.key.split(':')]
        other_key = [int(k) for k in other.key.split(':')]
        self_parent_key = self_key[:-1]
        other_parent_key = other_key[:-1]

        if self_parent_key and other_parent_key and \
                self_parent_key == other_parent_key:
            return self.value > other.value
        # if len(self_parent_key) < len(other_parent_key):
        #     return True
        # elif len(self_parent_key) > len(other_parent_key):
        #     return False
        return self_key > other_key

    def __lt__(self, other):
        return not self.__gt__(other)

    @property
    def name(self):
        return self.value

    @property
    def level(self):
        return len(self.key.split(':'))

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
            child = self.__class__.objects.create(id=_id, key=child_key, value=value)
            return child

    @classmethod
    def refresh_nodes(cls):
        cls.refresh_tree()

    def is_default_node(self):
        return self.is_root() and self.key == '1'

    def is_root(self):
        if self.key.isdigit():
            return True
        else:
            return False

    @classmethod
    def create_root_node(cls):
        # 如果使用current_org 在set_current_org时会死循环
        _current_org = get_current_org()
        with transaction.atomic():
            if not _current_org.is_real():
                return cls.default_node()
            set_current_org(Organization.root())
            org_nodes_roots = cls.objects.filter(key__regex=r'^[0-9]+$')
            org_nodes_roots_keys = org_nodes_roots.values_list('key', flat=True) or ['1']
            key = max([int(k) for k in org_nodes_roots_keys])
            key = str(key + 1) if key != 0 else '2'
            set_current_org(_current_org)
            root = cls.objects.create(key=key, value=_current_org.name)
            return root

    @classmethod
    def root(cls):
        root = cls.objects.filter(key__regex=r'^[0-9]+$')
        if root:
            return root[0]
        else:
            return cls.create_root_node()

    @classmethod
    def default_node(cls):
        defaults = {'value': 'Default'}
        obj, created = cls.objects.get_or_create(defaults=defaults, key='1')
        return obj

    def as_tree_node(self):
        from common.tree import TreeNode
        name = '{} ({})'.format(self.value, self.assets_amount)
        data = {
            'id': self.key,
            'name': name,
            'title': name,
            'pId': self.parent_key,
            'isParent': True,
            'open': self.is_root(),
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
