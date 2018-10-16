# -*- coding: utf-8 -*-
#
import uuid

from django.db import models, transaction
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.core.cache import cache

from orgs.mixins import OrgModelMixin
from orgs.utils import set_current_org, get_current_org
from orgs.models import Organization

__all__ = ['Node']


class Node(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    key = models.CharField(unique=True, max_length=64, verbose_name=_("Key"))  # '1:1:1:1'
    value = models.CharField(max_length=128, verbose_name=_("Value"))
    child_mark = models.IntegerField(default=0)
    date_create = models.DateTimeField(auto_now_add=True)

    is_node = True
    _full_value_cache_key_prefix = '_NODE_VALUE_{}'

    class Meta:
        verbose_name = _("Node")

    def __str__(self):
        return self.full_value

    def __eq__(self, other):
        if not other:
            return False
        return self.key == other.key

    def __gt__(self, other):
        if self.is_root():
            return True
        self_key = [int(k) for k in self.key.split(':')]
        other_key = [int(k) for k in other.key.split(':')]
        return self_key.__lt__(other_key)

    def __lt__(self, other):
        return not self.__gt__(other)

    @property
    def name(self):
        return self.value

    @property
    def full_value(self):
        key = self._full_value_cache_key_prefix.format(self.key)
        cached = cache.get(key)
        if cached:
            return cached
        value = self.get_full_value()
        self.cache_full_value(value)
        return value

    def get_full_value(self):
        # ancestor = [a.value for a in self.get_ancestor(with_self=True)]
        if self.is_root():
            return self.value
        parent_full_value = self.parent.full_value
        value = parent_full_value + ' / ' + self.value
        return value

    def cache_full_value(self, value):
        key = self._full_value_cache_key_prefix.format(self.key)
        cache.set(key, value, 3600)

    def expire_full_value(self):
        key = self._full_value_cache_key_prefix.format(self.key)
        cache.delete_pattern(key+'*')

    @property
    def level(self):
        return len(self.key.split(':'))

    def get_next_child_key(self):
        mark = self.child_mark
        self.child_mark += 1
        self.save()
        return "{}:{}".format(self.key, mark)

    def create_child(self, value):
        with transaction.atomic():
            child_key = self.get_next_child_key()
            child = self.__class__.objects.create(key=child_key, value=value)
            return child

    def get_children(self, with_self=False):
        pattern = r'^{0}$|^{}:[0-9]+$' if with_self else r'^{}:[0-9]+$'
        return self.__class__.objects.filter(
            key__regex=pattern.format(self.key)
        )

    def get_all_children(self, with_self=False):
        pattern = r'^{0}$|^{0}:' if with_self else r'^{0}'
        return self.__class__.objects.filter(
            key__regex=pattern.format(self.key)
        )

    def get_sibling(self, with_self=False):
        key = ':'.join(self.key.split(':')[:-1])
        pattern = r'^{}:[0-9]+$'.format(key)
        sibling = self.__class__.objects.filter(
            key__regex=pattern.format(self.key)
        )
        if not with_self:
            sibling = sibling.exclude(key=self.key)
        return sibling

    def get_family(self):
        ancestor = self.get_ancestor()
        children = self.get_all_children()
        return [*tuple(ancestor), self, *tuple(children)]

    def get_assets(self):
        from .asset import Asset
        if self.is_default_node():
            assets = Asset.objects.filter(nodes__isnull=True)
        else:
            assets = Asset.objects.filter(nodes__id=self.id)
        return assets

    def get_valid_assets(self):
        return self.get_assets().valid()

    def get_all_assets(self):
        from .asset import Asset
        pattern = r'^{0}$|^{0}:'.format(self.key)
        args = []
        kwargs = {}
        if self.is_default_node():
            args.append(Q(nodes__key__regex=pattern) | Q(nodes=None))
        else:
            kwargs['nodes__key__regex'] = pattern
        assets = Asset.objects.filter(*args, **kwargs).distinct()
        return assets

    def get_all_valid_assets(self):
        return self.get_all_assets().valid()

    def is_default_node(self):
        return self.is_root() and self.key == '0'

    def is_root(self):
        if self.key.isdigit():
            return True
        else:
            return False

    @property
    def parent_key(self):
        parent_key = ":".join(self.key.split(":")[:-1])
        return parent_key

    @property
    def parent(self):
        if self.is_root():
            return self
        try:
            parent = self.__class__.objects.get(key=self.parent_key)
            return parent
        except Node.DoesNotExist:
            return self.__class__.root()

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

    def get_ancestor(self, with_self=False):
        if self.is_root():
            root = self.__class__.root()
            return [root]
        _key = self.key.split(':')
        if not with_self:
            _key.pop()
        ancestor_keys = []
        for i in range(len(_key)):
            ancestor_keys.append(':'.join(_key))
            _key.pop()
        ancestor = self.__class__.objects.filter(
            key__in=ancestor_keys
        ).order_by('key')
        return ancestor

    @classmethod
    def create_root_node(cls):
        # 如果使用current_org 在set_current_org时会死循环
        _current_org = get_current_org()
        with transaction.atomic():
            if _current_org.is_root():
                key = '0'
            elif _current_org.is_default():
                key = '1'
            else:
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
        return cls.objects.get_or_create(defaults=defaults, key='1')

    @classmethod
    def get_tree_name_ref(cls):
        pass

    @classmethod
    def generate_fake(cls, count=100):
        import random
        for i in range(count):
            node = random.choice(cls.objects.all())
            node.create_child('Node {}'.format(i))


