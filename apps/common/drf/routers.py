# -*- coding: utf-8 -*-
#
from rest_framework.routers import DefaultRouter, DynamicRoute, Route
from rest_framework_nested.routers import NestedMixin
from rest_framework_bulk.routes import BulkRouter

__all__ = ['BulkNestDefaultRouter', 'SingletonRouter']


class BulkNestDefaultRouter(NestedMixin, BulkRouter):
    pass


class SingletonRouter(DefaultRouter):
    """Route singleton reads, updates and collection actions without a lookup."""

    routes = [
        Route(
            url=r'^{prefix}{trailing_slash}$',
            mapping={
                'get': 'list',
                'put': 'update',
                'patch': 'partial_update',
            },
            name='{basename}-list',
            detail=False,
            initkwargs={'suffix': 'Instance'},
        ),
        DynamicRoute(
            url=r'^{prefix}/{url_path}{trailing_slash}$',
            name='{basename}-{url_name}',
            detail=False,
            initkwargs={},
        ),
    ]
