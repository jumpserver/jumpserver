# -*- coding: utf-8 -*-
#
from rest_framework_nested.routers import NestedMixin
from rest_framework_bulk.routes import DefaultRouter

__all__ = ['BulkNestDefaultRouter']


class BulkNestDefaultRouter(NestedMixin, DefaultRouter):
    pass
