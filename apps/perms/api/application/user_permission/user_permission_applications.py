# -*- coding: utf-8 -*-
#
from typing import Callable

from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from common.mixins.api import CommonApiMixin
from common.tree import TreeNodeSerializer
from perms import serializers
from perms.tree.app import GrantedAppTreeUtil
from perms.utils.application.user_permission import (
    get_user_granted_all_applications
)
from .mixin import AppRoleAdminMixin, AppRoleUserMixin


__all__ = [
    'UserAllGrantedApplicationsApi',
    'MyAllGrantedApplicationsApi',
    'UserAllGrantedApplicationsAsTreeApi',
    'MyAllGrantedApplicationsAsTreeApi',
]


class AllGrantedApplicationsApi(CommonApiMixin, ListAPIView):
    only_fields = serializers.AppGrantedSerializer.Meta.only_fields
    serializer_class = serializers.AppGrantedSerializer
    filterset_fields = {
        'id': ['exact'],
        'name': ['exact'],
        'category': ['exact'],
        'type': ['exact', 'in'],
        'comment': ['exact'],
    }
    search_fields = ['name', 'comment']
    user: None

    def get_queryset(self):
        queryset = get_user_granted_all_applications(self.user)
        return queryset.only(*self.only_fields)


class UserAllGrantedApplicationsApi(AppRoleAdminMixin, AllGrantedApplicationsApi):
    pass


class MyAllGrantedApplicationsApi(AppRoleUserMixin, AllGrantedApplicationsApi):
    pass


class ApplicationsAsTreeMixin:
    """
    将应用序列化成树的结构返回
    """
    serializer_class = TreeNodeSerializer
    user: None
    filter_queryset: Callable
    get_queryset: Callable
    get_serializer: Callable

    def list(self, request, *args, **kwargs):
        tree_id = request.query_params.get('tree_id', None)
        parent_info = request.query_params.get('parentInfo', None)
        queryset = self.filter_queryset(self.get_queryset())
        util = GrantedAppTreeUtil()

        if not tree_id:
            tree_nodes = util.create_tree_nodes(queryset)
        else:
            tree_nodes = util.get_children_nodes(tree_id, parent_info, self.user)
        serializer = self.get_serializer(tree_nodes, many=True)
        return Response(data=serializer.data)


class UserAllGrantedApplicationsAsTreeApi(ApplicationsAsTreeMixin, UserAllGrantedApplicationsApi):
    pass


class MyAllGrantedApplicationsAsTreeApi(ApplicationsAsTreeMixin, MyAllGrantedApplicationsApi):
    pass
