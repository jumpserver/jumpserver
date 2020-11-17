# -*- coding: utf-8 -*-
#
import abc
from django.conf import settings
from rest_framework.generics import (
    ListAPIView
)
from rest_framework.response import Response
from rest_framework.request import Request

from assets.api.mixin import SerializeToTreeNodeMixin
from common.utils import get_logger
from .mixin import ForAdminMixin, ForUserMixin, UserNodeGrantStatusDispatchMixin
from perms.hands import Node, User
from perms import serializers
from perms.utils.asset.user_permission import (
    get_indirect_granted_node_children,
    get_user_granted_nodes_list_via_mapping_node,
    get_top_level_granted_nodes,
    rebuild_user_tree_if_need, get_favorite_node,
    get_ungrouped_node
)


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
        rebuild_user_tree_if_need(request, self.user)
        nodes = self.get_nodes()
        serializer = self.get_serializer(nodes, many=True)
        return Response(serializer.data)


class BaseNodeChildrenApi(NodeChildrenMixin, BaseGrantedNodeApi, metaclass=abc.ABCMeta):
    pass


class BaseGrantedNodeAsTreeApi(SerializeToTreeNodeMixin, _GrantedNodeStructApi, metaclass=abc.ABCMeta):
    def list(self, request: Request, *args, **kwargs):
        rebuild_user_tree_if_need(request, self.user)
        nodes = self.get_nodes()
        nodes = self.serialize_nodes(nodes, with_asset_amount=True)
        return Response(data=nodes)


class BaseNodeChildrenAsTreeApi(NodeChildrenMixin, BaseGrantedNodeAsTreeApi, metaclass=abc.ABCMeta):
    pass


class UserGrantedNodeChildrenMixin(UserNodeGrantStatusDispatchMixin):
    user: User
    request: Request

    def get_children(self):
        user = self.user
        key = self.request.query_params.get('key')

        if not key:
            nodes = list(get_top_level_granted_nodes(user))
        else:
            nodes = self.dispatch_get_data(key, user)
        return nodes

    def get_data_on_node_direct_granted(self, key):
        return Node.objects.filter(parent_key=key)

    def get_data_on_node_indirect_granted(self, key):
        nodes = get_indirect_granted_node_children(self.user, key)
        return nodes

    def get_data_on_node_not_granted(self, key):
        return Node.objects.none()


class UserGrantedNodesMixin:
    """
    查询用户授权的所有节点 直接授权节点 + 授权资产关联的节点
    """
    user: User

    def get_nodes(self):
        nodes = []
        if settings.PERM_SINGLE_ASSET_TO_UNGROUP_NODE:
            nodes.append(get_ungrouped_node(self.user))
        nodes.append(get_favorite_node(self.user))
        nodes.extend(get_user_granted_nodes_list_via_mapping_node(self.user))
        return nodes


# ------------------------------------------
# 最终的 api
class UserGrantedNodeChildrenForAdminApi(ForAdminMixin, UserGrantedNodeChildrenMixin, BaseNodeChildrenApi):
    pass


class MyGrantedNodeChildrenApi(ForUserMixin, UserGrantedNodeChildrenMixin, BaseNodeChildrenApi):
    pass


class UserGrantedNodeChildrenAsTreeForAdminApi(ForAdminMixin, UserGrantedNodeChildrenMixin, BaseNodeChildrenAsTreeApi):
    pass


class MyGrantedNodeChildrenAsTreeApi(ForUserMixin, UserGrantedNodeChildrenMixin, BaseNodeChildrenAsTreeApi):
    pass


class UserGrantedNodesForAdminApi(ForAdminMixin, UserGrantedNodesMixin, BaseGrantedNodeApi):
    pass


class MyGrantedNodesApi(ForUserMixin, UserGrantedNodesMixin, BaseGrantedNodeApi):
    pass


class MyGrantedNodesAsTreeApi(ForUserMixin, UserGrantedNodesMixin, BaseGrantedNodeAsTreeApi):
    pass

# ------------------------------------------
