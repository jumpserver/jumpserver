from rest_framework.response import Response

from assets.api import SerializeToTreeNodeMixin
from common.utils import get_logger

from .mixin import RebuildTreeMixin
from ..nodes import (
    UserAllPermedNodesApi,
    UserPermedNodeChildrenApi,
)

logger = get_logger(__name__)

__all__ = [
    'UserAllPermedNodesAsTreeApi',
    'UserPermedNodeChildrenAsTreeApi',
]


class NodeTreeMixin(RebuildTreeMixin, SerializeToTreeNodeMixin):
    filter_queryset: callable
    get_queryset: callable

    def list(self, request, *args, **kwargs):
        nodes = self.filter_queryset(self.get_queryset())
        data = self.serialize_nodes(nodes, with_asset_amount=True)
        return Response(data)


class UserAllPermedNodesAsTreeApi(NodeTreeMixin, UserAllPermedNodesApi):
    """ 用户 '授权的节点' 作为树 """
    pass


class UserPermedNodeChildrenAsTreeApi(NodeTreeMixin, UserPermedNodeChildrenApi):
    """ 用户授权的节点下的子节点树 """
    pass


