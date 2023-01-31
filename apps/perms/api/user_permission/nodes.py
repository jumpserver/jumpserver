# -*- coding: utf-8 -*-
#
import abc

from rest_framework.generics import ListAPIView

from assets.models import Node
from common.utils import get_logger, lazyproperty
from perms import serializers
from perms.utils import UserPermNodeUtil
from .mixin import SelfOrPKUserMixin

logger = get_logger(__name__)

__all__ = [
    'UserAllPermedNodesApi',
    'UserPermedNodeChildrenApi',
]


class BaseUserPermedNodesApi(SelfOrPKUserMixin, ListAPIView):
    serializer_class = serializers.NodePermedSerializer

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Node.objects.none()
        return self.get_nodes()

    @abc.abstractmethod
    def get_nodes(self):
        return []

    @lazyproperty
    def query_node_util(self):
        return UserPermNodeUtil(self.user)


class UserAllPermedNodesApi(BaseUserPermedNodesApi):
    """ 用户授权的节点 """

    def get_nodes(self):
        return self.query_node_util.get_whole_tree_nodes()


class UserPermedNodeChildrenApi(BaseUserPermedNodesApi):
    """ 用户授权的节点下的子节点 """

    def get_nodes(self):
        key = self.request.query_params.get('key')
        nodes = self.query_node_util.get_node_children(key)
        return nodes
