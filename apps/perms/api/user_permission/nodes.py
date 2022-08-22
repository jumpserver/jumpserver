# -*- coding: utf-8 -*-
#
import abc
from rest_framework.generics import (
    ListAPIView
)
from rest_framework.response import Response
from rest_framework.request import Request

from assets.api.mixin import SerializeToTreeNodeMixin
from common.utils import get_logger
from .mixin import AssetRoleAdminMixin, AssetRoleUserMixin
from perms.hands import User
from perms import serializers

from perms.utils.asset.user_permission import UserGrantedNodesQueryUtils


logger = get_logger(__name__)

__all__ = [
    'UserGrantedNodesForAdminApi',
    'MyGrantedNodesApi',
    'MyGrantedNodesAsTreeApi',
    'UserGrantedNodeChildrenForAdminApi',
    'MyGrantedNodeChildrenApi',
    'UserGrantedNodeChildrenAsTreeForAdminApi',
    'MyGrantedNodeChildrenAsTreeApi',
    'BaseGrantedNodeAsTreeApi',
    'UserGrantedNodesMixin',
]


class _GrantedNodeStructApi(ListAPIView, metaclass=abc.ABCMeta):
    @property
    def user(self):
        raise NotImplementedError

    def get_nodes(self):
        # 不使用 `get_queryset` 单独定义 `get_nodes` 的原因是
        # `get_nodes` 返回的不一定是 `queryset`
        raise NotImplementedError


class NodeChildrenMixin:
    def get_children(self):
        raise NotImplementedError

    def get_nodes(self):
        nodes = self.get_children()
        return nodes


class BaseGrantedNodeApi(_GrantedNodeStructApi, metaclass=abc.ABCMeta):
    serializer_class = serializers.NodeGrantedSerializer

    def list(self, request, *args, **kwargs):
        nodes = self.get_nodes()
        serializer = self.get_serializer(nodes, many=True)
        return Response(serializer.data)


class BaseNodeChildrenApi(NodeChildrenMixin, BaseGrantedNodeApi, metaclass=abc.ABCMeta):
    pass


class BaseGrantedNodeAsTreeApi(SerializeToTreeNodeMixin, _GrantedNodeStructApi, metaclass=abc.ABCMeta):
    def list(self, request: Request, *args, **kwargs):
        nodes = self.get_nodes()
        nodes = self.serialize_nodes(nodes, with_asset_amount=True)
        return Response(data=nodes)


class BaseNodeChildrenAsTreeApi(NodeChildrenMixin, BaseGrantedNodeAsTreeApi, metaclass=abc.ABCMeta):
    pass


class UserGrantedNodeChildrenMixin:
    user: User
    request: Request

    def get_children(self):
        user = self.user
        key = self.request.query_params.get('key')
        nodes = UserGrantedNodesQueryUtils(user).get_node_children(key)
        return nodes


class UserGrantedNodesMixin:
    """
    查询用户授权的所有节点 直接授权节点 + 授权资产关联的节点
    """
    user: User

    def get_nodes(self):
        utils = UserGrantedNodesQueryUtils(self.user)
        nodes = utils.get_whole_tree_nodes()
        return nodes


# ------------------------------------------
# 最终的 api
class UserGrantedNodeChildrenForAdminApi(AssetRoleAdminMixin, UserGrantedNodeChildrenMixin, BaseNodeChildrenApi):
    pass


class MyGrantedNodeChildrenApi(AssetRoleUserMixin, UserGrantedNodeChildrenMixin, BaseNodeChildrenApi):
    pass


class UserGrantedNodeChildrenAsTreeForAdminApi(AssetRoleAdminMixin, UserGrantedNodeChildrenMixin, BaseNodeChildrenAsTreeApi):
    pass


class MyGrantedNodeChildrenAsTreeApi(AssetRoleUserMixin, UserGrantedNodeChildrenMixin, BaseNodeChildrenAsTreeApi):
    def get_permissions(self):
        permissions = super().get_permissions()
        return permissions


class UserGrantedNodesForAdminApi(AssetRoleAdminMixin, UserGrantedNodesMixin, BaseGrantedNodeApi):
    pass


class MyGrantedNodesApi(AssetRoleUserMixin, UserGrantedNodesMixin, BaseGrantedNodeApi):
    pass


class MyGrantedNodesAsTreeApi(AssetRoleUserMixin, UserGrantedNodesMixin, BaseGrantedNodeAsTreeApi):
    pass

# ------------------------------------------
