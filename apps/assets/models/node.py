# -*- coding: utf-8 -*-
#
import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _


__all__ = ['Node']


class Node(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    key = models.CharField(unique=True, max_length=64, verbose_name=_("Key"))  # '1:1:1:1'
    value = models.CharField(max_length=128, unique=True, verbose_name=_("Value"))
    child_mark = models.IntegerField(default=0)
    date_create = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.value

    @property
    def name(self):
        return self.value

    @property
    def full_value(self):
        if self == self.__class__.root():
            return self.value
        else:
            return '{}/{}'.format(self.value, self.parent.full_value)

    @property
    def level(self):
        return len(self.key.split(':'))

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
        return self.__class__.objects.filter(key__regex=r'{}:[0-9]+$'.format(self.key))

    def get_all_children(self):
        return self.__class__.objects.filter(key__startswith='{}:'.format(self.key))

    def get_family(self):
        children = list(self.get_all_children())
        children.append(self)
        return children

    def get_assets(self):
        from .asset import Asset
        assets = Asset.objects.filter(nodes__id=self.id)
        return assets

    def get_active_assets(self):
        return self.get_assets().filter(is_active=True)

    def get_all_assets(self):
        from .asset import Asset
        if self.is_root():
            assets = Asset.objects.all()
        else:
            nodes = self.get_family()
            assets = Asset.objects.filter(nodes__in=nodes)
        return assets

    def get_all_active_assets(self):
        return self.get_all_assets().filter(is_active=True)

    def is_root(self):
        return self.key == '0'

    @property
    def parent(self):
        if self.key == "0":
            return self.__class__.root()
        elif not self.key.startswith("0"):
            return self.__class__.root()

        parent_key = ":".join(self.key.split(":")[:-1])
        try:
            parent = self.__class__.objects.get(key=parent_key)
        except Node.DoesNotExist:
            return self.__class__.root()
        else:
            return parent

    @parent.setter
    def parent(self, parent):
        self.key = parent.get_next_child_key()

    @property
    def ancestor(self):
        if self.parent == self.__class__.root():
            return [self.__class__.root()]
        else:
            return [self.parent, *tuple(self.parent.ancestor)]

    @property
    def ancestor_with_node(self):
        ancestor = self.ancestor
        ancestor.insert(0, self)
        return ancestor

    @classmethod
    def root(cls):
        obj, created = cls.objects.get_or_create(
            key='0', defaults={"key": '0', 'value': "ROOT"}
        )
        return obj
