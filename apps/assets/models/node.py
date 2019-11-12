# -*- coding: utf-8 -*-
#
import uuid
import re
import time

from django.db import models, transaction
from django.db.models import Q
from django.db.utils import IntegrityError
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from django.core.cache import cache

from common.utils import get_logger, timeit, lazyproperty
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
        logger.debug("Refresh node assets")
        key = cls.tree_assets_cache_key
        ttl = cls.tree_cache_time
        if not t:
            t = time.time()
        cache.set(key, t, ttl)

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

    @classmethod
    def get_node_all_children_key_pattern(cls, key, with_self=True):
        pattern = r'^{0}:'.format(key)
        if with_self:
            pattern += r'|^{0}$'.format(key)
        return pattern

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
        pattern = self.get_children_key_pattern(with_self=with_self)
        return Node.objects.filter(key__regex=pattern)

    def get_all_children(self, with_self=False):
        pattern = self.get_all_children_pattern(with_self=with_self)
        children = Node.objects.filter(key__regex=pattern)
        return children

    @property
    def children(self):
        return self.get_children(with_self=False)

    @property
    def all_children(self):
        return self.get_all_children(with_self=False)

    def create_child(self, value, _id=None):
        with transaction.atomic():
            child_key = self.get_next_child_key()
            child = self.__class__.objects.create(
                id=_id, key=child_key, value=value
            )
            return child

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
        return self.get_node_ancestor_keys(
            self.key, with_self=with_self
        )

    @property
    def ancestors(self):
        return self.get_ancestors(with_self=False)

    def get_ancestors(self, with_self=False):
        ancestor_keys = self.get_ancestor_keys(with_self=with_self)
        return self.__class__.objects.filter(key__in=ancestor_keys)

    @property
    def parent_key(self):
        parent_key = ":".join(self.key.split(":")[:-1])
        return parent_key

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

    def get_family(self):
        ancestors = self.get_ancestors()
        children = self.get_all_children()
        return [*tuple(ancestors), self, *tuple(children)]


class FullValueMixin:
    key = ''

    @lazyproperty
    def full_value(self):
        if self.is_org_root():
            return self.value
        value = self.tree().get_node_full_tag(self.key)
        return value


class NodeAssetsMixin:
    key = ''
    id = None

    @lazyproperty
    def assets_amount(self):
        amount = self.tree().assets_amount(self.key)
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
    def _get_nodes_all_assets(cls, nodes_keys):
        """
        当节点比较多的时候，这种正则方式性能差极了
        :param nodes_keys:
        :return:
        """
        from .asset import Asset
        nodes_keys = cls.clean_children_keys(nodes_keys)
        nodes_children_pattern = set()
        for key in nodes_keys:
            children_pattern = cls.get_node_all_children_key_pattern(key)
            nodes_children_pattern.add(children_pattern)
        pattern = '|'.join(nodes_children_pattern)
        return Asset.objects.filter(nodes__key__regex=pattern).distinct()

    @classmethod
    def get_nodes_all_assets_ids(cls, nodes_keys):
        nodes_keys = cls.clean_children_keys(nodes_keys)
        assets_ids = set()
        for key in nodes_keys:
            node_assets_ids = cls.tree().all_assets(key)
            assets_ids.update(set(node_assets_ids))
        return assets_ids

    @classmethod
    def get_nodes_all_assets(cls, nodes_keys, extra_assets_ids=None):
        from .asset import Asset
        nodes_keys = cls.clean_children_keys(nodes_keys)
        assets_ids = cls.get_nodes_all_assets_ids(nodes_keys)
        if extra_assets_ids:
            assets_ids.update(set(extra_assets_ids))
        return Asset.objects.filter(id__in=assets_ids)


class SomeNodesMixin:
    key = ''
    default_key = '1'
    default_value = 'Default'
    ungrouped_key = '-10'
    ungrouped_value = _('ungrouped')
    empty_key = '-11'
    empty_value = _("empty")
    favorite_key = '-12'
    favorite_value = _("favorite")

    def is_default_node(self):
        return self.key == self.default_key

    def is_org_root(self):
        if self.key.isdigit():
            return True
        else:
            return False

    @classmethod
    def get_next_org_root_node_key(cls):
        with tmp_to_org(Organization.root()):
            org_nodes_roots = cls.objects.filter(key__regex=r'^[0-9]+$')
            org_nodes_roots_keys = org_nodes_roots.values_list('key', flat=True)
            if not org_nodes_roots_keys:
                org_nodes_roots_keys = ['1']
            max_key = max([int(k) for k in org_nodes_roots_keys])
            key = str(max_key + 1) if max_key != 0 else '2'
            return key

    @classmethod
    def create_org_root_node(cls):
        # 如果使用current_org 在set_current_org时会死循环
        ori_org = get_current_org()
        with transaction.atomic():
            if not ori_org.is_real():
                return cls.default_node()
            key = cls.get_next_org_root_node_key()
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
            defaults = {'value': cls.ungrouped_value}
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
            try:
                obj, created = cls.objects.get_or_create(
                    defaults=defaults, key=cls.default_key,
                )
            except IntegrityError as e:
                logger.error("Create default node failed: {}".format(e))
                cls.modify_other_org_root_node_key()
                obj, created = cls.objects.get_or_create(
                    defaults=defaults, key=cls.default_key,
                )
            return obj

    @classmethod
    def favorite_node(cls):
        with tmp_to_org(Organization.system()):
            defaults = {'value': cls.favorite_value}
            obj, created = cls.objects.get_or_create(
                defaults=defaults, key=cls.favorite_key
            )
            return obj

    @classmethod
    def initial_some_nodes(cls):
        cls.default_node()
        cls.empty_node()
        cls.ungrouped_node()
        cls.favorite_node()

    @classmethod
    def modify_other_org_root_node_key(cls):
        """
        解决创建 default 节点失败的问题，
        因为在其他组织下存在 default 节点，故在 DEFAULT 组织下 get 不到 create 失败
        """
        logger.info("Modify other org root node key")

        with tmp_to_org(Organization.root()):
            node_key1 = cls.objects.filter(key='1').first()
            if not node_key1:
                logger.info("Not found node that `key` = 1")
                return
            if not node_key1.org.is_real():
                logger.info("Org is not real for node that `key` = 1")
                return

        with transaction.atomic():
            with tmp_to_org(node_key1.org):
                org_root_node_new_key = cls.get_next_org_root_node_key()
                for n in cls.objects.all():
                    old_key = n.key
                    key_list = n.key.split(':')
                    key_list[0] = org_root_node_new_key
                    new_key = ':'.join(key_list)
                    n.key = new_key
                    n.save()
                    logger.info('Modify key ( {} > {} )'.format(old_key, new_key))


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

    # def __eq__(self, other):
    #     if not other:
    #         return False
    #     return self.id == other.id
    #
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

    def has_children_or_contains_assets(self):
        if self.children or self.get_assets():
            return True
        return False

    def delete(self, using=None, keep_parents=False):
        if self.has_children_or_contains_assets():
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
