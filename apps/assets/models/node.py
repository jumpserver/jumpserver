# -*- coding: utf-8 -*-
#
import uuid
import re

from django.db import models, transaction
from django.db.models import Q
from django.db.utils import IntegrityError
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from django.db.transaction import atomic

from common.utils import get_logger
from common.utils.common import lazyproperty
from orgs.mixins.models import OrgModelMixin, OrgManager
from orgs.utils import get_current_org, tmp_to_org
from orgs.models import Organization


__all__ = ['Node', 'FamilyMixin', 'compute_parent_key', 'NodeAssetRelatedRecord']
logger = get_logger(__name__)


def compute_parent_key(key):
    try:
        return key[:key.rindex(':')]
    except ValueError:
        return ''


class NodeQuerySet(models.QuerySet):
    def delete(self):
        raise NotImplementedError


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

    # @property
    # def parent_key(self):
    #     parent_key = ":".join(self.key.split(":")[:-1])
    #     return parent_key

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


class NodeAssetsMixin:
    key = ''
    id = None

    def get_all_assets(self):
        from .asset import Asset
        q = Q(nodes__key__startswith=f'{self.key}:') | Q(nodes__key=self.key)
        return Asset.objects.filter(q).distinct()

    @classmethod
    def get_node_all_assets_by_key_v2(cls, key):
        # 最初的写法是：
        #   Asset.objects.filter(Q(nodes__key__startswith=f'{node.key}:') | Q(nodes__id=node.id))
        #   可是 startswith 会导致表关联时 Asset 索引失效
        from .asset import Asset
        node_ids = cls.objects.filter(
            Q(key__startswith=f'{key}:') |
            Q(key=key)
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
    def get_nodes_all_assets_ids(cls, nodes_keys):
        assets_ids = cls.get_nodes_all_assets(nodes_keys).values_list('id', flat=True)
        return assets_ids

    @classmethod
    def get_nodes_all_assets(cls, nodes_keys, extra_assets_ids=None):
        from .asset import Asset
        nodes_keys = cls.clean_children_keys(nodes_keys)
        q = Q()
        node_ids = ()
        for key in nodes_keys:
            q |= Q(key__startswith=f'{key}:')
            q |= Q(key=key)
        if q:
            node_ids = Node.objects.filter(q).distinct().values_list('id', flat=True)

        q = Q(nodes__id__in=list(node_ids))
        if extra_assets_ids:
            q |= Q(id__in=extra_assets_ids)
        if q:
            return Asset.org_objects.filter(q).distinct()
        else:
            return Asset.objects.none()


class SomeNodesMixin:
    key = ''
    default_key = '1'
    default_value = 'Default'
    empty_key = '-11'
    empty_value = _("empty")

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
        root = cls.objects.filter(parent_key='')\
            .filter(key__regex=r'^[0-9]+$')\
            .exclude(key__startswith='-')\
            .order_by('key')
        if root:
            return root[0]
        else:
            return cls.create_org_root_node()

    @classmethod
    def initial_some_nodes(cls):
        cls.default_node()

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


class Node(OrgModelMixin, SomeNodesMixin, FamilyMixin, NodeAssetsMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    key = models.CharField(unique=True, max_length=64, verbose_name=_("Key"))  # '1:1:1:1'
    value = models.CharField(max_length=128, verbose_name=_("Value"))
    full_value = models.CharField(max_length=4096, verbose_name=_('Full value'), default='')
    child_mark = models.IntegerField(default=0)
    date_create = models.DateTimeField(auto_now_add=True)
    parent_key = models.CharField(max_length=64, verbose_name=_("Parent key"),
                                  db_index=True, default='')
    assets_amount = models.IntegerField(default=0)

    objects = OrgManager.from_queryset(NodeQuerySet)()
    is_node = True
    _parents = None

    class Meta:
        verbose_name = _("Node")
        ordering = ['parent_key', 'value']

    def __str__(self):
        return self.full_value

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

    def has_children_or_has_assets(self):
        if self.children or self.get_assets().exists():
            return True
        return False

    def delete(self, using=None, keep_parents=False):
        if self.has_children_or_has_assets():
            return
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


class NodeAssetRelatedRecord(models.Model):
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, related_name='nodes_related_records')
    node = models.ForeignKey('assets.Node', on_delete=models.CASCADE, related_name='assets_related_records')
    related_count = models.IntegerField(default=0)
