# -*- coding: utf-8 -*-
#
import uuid

from django.db import models, transaction
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _


__all__ = ['Node']


class Node(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    key = models.CharField(unique=True, max_length=64, verbose_name=_("Key"))  # '1:1:1:1'
    # value = models.CharField(
    #     max_length=128, unique=True, verbose_name=_("Value")
    # )
    value = models.CharField(max_length=128, verbose_name=_("Value"))
    child_mark = models.IntegerField(default=0)
    date_create = models.DateTimeField(auto_now_add=True)

    is_node = True

    def __str__(self):
        return self.full_value

    @property
    def name(self):
        return self.value

    @property
    def full_value(self):
        if self == self.__class__.root():
            return self.value
        else:
            return '{} / {}'.format(self.parent.full_value, self.value)

    @property
    def level(self):
        return len(self.key.split(':'))

    def set_parent(self, instance):
        children = self.get_all_children()
        old_key = self.key
        with transaction.atomic():
            self.parent = instance
            for child in children:
                child.key = child.key.replace(old_key, self.key, 1)
                child.save()
            self.save()

    def get_next_child_key(self):
        mark = self.child_mark
        self.child_mark += 1
        self.save()
        return "{}:{}".format(self.key, mark)

    def create_child(self, value):
        child_key = self.get_next_child_key()
        child = self.__class__.objects.create(key=child_key, value=value)
        return child

    def get_children(self):
        return self.__class__.objects.filter(
            key__regex=r'^{}:[0-9]+$'.format(self.key)
        )

    def get_children_with_self(self):
        return self.__class__.objects.filter(
            key__regex=r'^{0}$|^{0}:[0-9]+$'.format(self.key)
        )

    def get_all_children(self):
        return self.__class__.objects.filter(
            key__startswith='{}:'.format(self.key)
        )

    def get_all_children_with_self(self):
        return self.__class__.objects.filter(
            key__regex=r'^{0}$|^{0}:'.format(self.key)
        )

    def get_family(self):
        ancestor = self.ancestor
        children = self.get_all_children()
        return [*tuple(ancestor), self, *tuple(children)]

    def get_assets(self):
        from .asset import Asset
        if self.is_root():
            assets = Asset.objects.filter(
                Q(nodes__id=self.id) | Q(nodes__isnull=True)
            )
        else:
            assets = Asset.objects.filter(nodes__id=self.id)
        return assets

    def get_valid_assets(self):
        return self.get_assets().valid()

    def get_all_assets(self):
        from .asset import Asset
        if self.is_root():
            assets = Asset.objects.all()
        else:
            nodes = self.get_all_children_with_self()
            assets = Asset.objects.filter(nodes__in=nodes).distinct()
        return assets

    def get_current_assets(self):
        from .asset import Asset
        assets = Asset.objects.filter(nodes=self).distinct()
        return assets

    def has_assets(self):
        return self.get_all_assets()

    def get_all_valid_assets(self):
        return self.get_all_assets().valid()

    def is_root(self):
        return self.key == '0'

    @property
    def parent(self):
        if self.key == "0" or not self.key.startswith("0"):
            return self.__class__.root()

        parent_key = ":".join(self.key.split(":")[:-1])
        try:
            parent = self.__class__.objects.get(key=parent_key)
            return parent
        except Node.DoesNotExist:
            return self.__class__.root()

    @parent.setter
    def parent(self, parent):
        self.key = parent.get_next_child_key()

    @property
    def ancestor(self):
        _key = self.key.split(':')
        ancestor_keys = []

        if self.is_root():
            return [self.__class__.root()]

        for i in range(len(_key)-1):
            _key.pop()
            ancestor_keys.append(':'.join(_key))
        return self.__class__.objects.filter(key__in=ancestor_keys)

    @property
    def ancestor_with_self(self):
        ancestor = list(self.ancestor)
        ancestor.insert(0, self)
        return ancestor

    @classmethod
    def root(cls):
        obj, created = cls.objects.get_or_create(
            key='0', defaults={"key": '0', 'value': "ROOT"}
        )
        return obj
