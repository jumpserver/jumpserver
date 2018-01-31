# -*- coding: utf-8 -*-
#

from django.db import models
from django.utils.translation import ugettext_lazy as _


__all__ = ['Node']


class Node(models.Model):
    id = models.CharField(primary_key=True, max_length=64)  # '1:1:1:1'
    name = models.CharField(max_length=128, verbose_name=_("Name"))
    child_mark = models.IntegerField(default=0)
    date_create = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    @property
    def level(self):
        return len(self.id.split(':'))

    def get_next_child_id(self):
        mark = self.child_mark
        self.child_mark += 1
        self.save()
        return "{}:{}".format(self.id, mark)

    def create_child(self, name):
        child_id = self.get_next_child_id()
        child = self.__class__.objects.create(id=child_id, name=name)
        return child

    def get_children(self):
        return self.__class__.objects.filter(id__regex=r'{}:[0-9]+$'.format(self.id))

    def get_all_children(self):
        return self.__class__.objects.filter(id__startswith='{}:'.format(self.id))

    def get_assets(self):
        from .asset import Asset
        children = self.get_children()
        assets = Asset.objects.filter(nodes__in=children)
        return assets

    def get_all_assets(self):
        from .asset import Asset
        children = self.get_all_children()
        assets = Asset.objects.filter(nodes__in=children)
        return assets

    @classmethod
    def get_root_node(cls):
        obj, created = cls.objects.get_or_create(
            id='0', defaults={"id": '0', 'name': "ROOT"}
        )
        return obj
