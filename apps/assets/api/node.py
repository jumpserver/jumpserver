# ~*~ coding: utf-8 ~*~
# Copyright (C) 2014-2018 Beijing DuiZhan Technology Co.,Ltd. All Rights Reserved.
#
# Licensed under the GNU General Public License v2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.gnu.org/licenses/gpl-2.0.html
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from rest_framework import status
from rest_framework.serializers import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404

from common.utils import get_logger, get_object_or_none
from common.tree import TreeNodeSerializer
from orgs.mixins.api import OrgModelViewSet
from orgs.mixins import generics
from ..hands import IsOrgAdmin
from ..models import Node
from ..tasks import (
    update_assets_hardware_info_util, test_asset_connectivity_util
)
from .. import serializers


logger = get_logger(__file__)
__all__ = [
    'NodeViewSet', 'NodeChildrenApi', 'NodeAssetsApi',
    'NodeAddAssetsApi', 'NodeRemoveAssetsApi', 'NodeReplaceAssetsApi',
    'NodeAddChildrenApi', 'RefreshNodeHardwareInfoApi',
    'TestNodeConnectiveApi', 'NodeListAsTreeApi',
    'NodeChildrenAsTreeApi', 'RefreshNodesCacheApi',
]


class NodeViewSet(OrgModelViewSet):
    model = Node
    filter_fields = ('value', 'key', 'id')
    search_fields = ('value', )
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.NodeSerializer

    # 仅支持根节点指直接创建，子节点下的节点需要通过children接口创建
    def perform_create(self, serializer):
        child_key = Node.org_root().get_next_child_key()
        serializer.validated_data["key"] = child_key
        serializer.save()

    def perform_update(self, serializer):
        node = self.get_object()
        if node.is_org_root() and node.value != serializer.validated_data['value']:
            msg = _("You can't update the root node name")
            raise ValidationError({"error": msg})
        return super().perform_update(serializer)

    def destroy(self, request, *args, **kwargs):
        node = self.get_object()
        if node.has_children_or_contains_assets():
            msg = _("Deletion failed and the node contains children or assets")
            return Response(data={'msg': msg}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class NodeListAsTreeApi(generics.ListAPIView):
    """
    获取节点列表树
    [
      {
        "id": "",
        "name": "",
        "pId": "",
        "meta": ""
      }
    ]
    """
    model = Node
    permission_classes = (IsOrgAdmin,)
    serializer_class = TreeNodeSerializer

    @staticmethod
    def to_tree_queryset(queryset):
        queryset = [node.as_tree_node() for node in queryset]
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = self.to_tree_queryset(queryset)
        return queryset


class NodeChildrenApi(generics.ListCreateAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.NodeSerializer
    instance = None
    is_initial = False

    def initial(self, request, *args, **kwargs):
        self.instance = self.get_object()
        return super().initial(request, *args, **kwargs)

    def perform_create(self, serializer):
        data = serializer.validated_data
        _id = data.get("id")
        value = data.get("value")
        if not value:
            value = self.instance.get_next_child_preset_name()
        node = self.instance.create_child(value=value, _id=_id)
        # 避免查询 full value
        node._full_value = node.value
        serializer.instance = node

    def get_object(self):
        pk = self.kwargs.get('pk') or self.request.query_params.get('id')
        key = self.request.query_params.get("key")
        if not pk and not key:
            node = Node.org_root()
            self.is_initial = True
            return node
        if pk:
            node = get_object_or_404(Node, pk=pk)
        else:
            node = get_object_or_404(Node, key=key)
        return node

    def get_queryset(self):
        query_all = self.request.query_params.get("all", "0") == "all"
        if not self.instance:
            return Node.objects.none()

        if self.is_initial:
            with_self = True
        else:
            with_self = False

        if query_all:
            queryset = self.instance.get_all_children(with_self=with_self)
        else:
            queryset = self.instance.get_children(with_self=with_self)
        return queryset


class NodeChildrenAsTreeApi(NodeChildrenApi):
    """
    节点子节点作为树返回，
    [
      {
        "id": "",
        "name": "",
        "pId": "",
        "meta": ""
      }
    ]

    """
    model = Node
    serializer_class = TreeNodeSerializer
    http_method_names = ['get']

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = [node.as_tree_node() for node in queryset]
        queryset = self.add_assets_if_need(queryset)
        queryset = sorted(queryset)
        return queryset

    def add_assets_if_need(self, queryset):
        include_assets = self.request.query_params.get('assets', '0') == '1'
        if not include_assets:
            return queryset
        assets = self.instance.get_assets().only(
            "id", "hostname", "ip", "os",
            "org_id", "protocols",
        )
        for asset in assets:
            queryset.append(asset.as_tree_node(self.instance))
        return queryset

    def check_need_refresh_nodes(self):
        if self.request.query_params.get('refresh', '0') == '1':
            Node.refresh_nodes()


class NodeAssetsApi(generics.ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetSerializer

    def get_queryset(self):
        node_id = self.kwargs.get('pk')
        query_all = self.request.query_params.get('all')
        instance = get_object_or_404(Node, pk=node_id)
        if query_all:
            return instance.get_all_assets()
        else:
            return instance.get_assets()


class NodeAddChildrenApi(generics.UpdateAPIView):
    model = Node
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.NodeAddChildrenSerializer
    instance = None

    def put(self, request, *args, **kwargs):
        instance = self.get_object()
        nodes_id = request.data.get("nodes")
        children = [get_object_or_none(Node, id=pk) for pk in nodes_id]
        for node in children:
            if not node:
                continue
            node.parent = instance
        return Response("OK")


class NodeAddAssetsApi(generics.UpdateAPIView):
    model = Node
    serializer_class = serializers.NodeAssetsSerializer
    permission_classes = (IsOrgAdmin,)
    instance = None

    def perform_update(self, serializer):
        assets = serializer.validated_data.get('assets')
        instance = self.get_object()
        instance.assets.add(*tuple(assets))


class NodeRemoveAssetsApi(generics.UpdateAPIView):
    model = Node
    serializer_class = serializers.NodeAssetsSerializer
    permission_classes = (IsOrgAdmin,)
    instance = None

    def perform_update(self, serializer):
        assets = serializer.validated_data.get('assets')
        instance = self.get_object()
        if instance != Node.org_root():
            instance.assets.remove(*tuple(assets))
        else:
            assets = [asset for asset in assets if asset.nodes.count() > 1]
            instance.assets.remove(*tuple(assets))


class NodeReplaceAssetsApi(generics.UpdateAPIView):
    model = Node
    serializer_class = serializers.NodeAssetsSerializer
    permission_classes = (IsOrgAdmin,)
    instance = None

    def perform_update(self, serializer):
        assets = serializer.validated_data.get('assets')
        instance = self.get_object()
        for asset in assets:
            asset.nodes.set([instance])


class RefreshNodeHardwareInfoApi(APIView):
    model = Node
    permission_classes = (IsOrgAdmin,)

    def get(self, request, *args, **kwargs):
        node_id = kwargs.get('pk')
        node = get_object_or_404(self.model, id=node_id)
        assets = node.get_all_assets()
        # task_name = _("更新节点资产硬件信息: {}".format(node.name))
        task_name = _("Update node asset hardware information: {}").format(node.name)
        task = update_assets_hardware_info_util.delay(assets, task_name=task_name)
        return Response({"task": task.id})


class TestNodeConnectiveApi(APIView):
    permission_classes = (IsOrgAdmin,)
    model = Node

    def get(self, request, *args, **kwargs):
        node_id = kwargs.get('pk')
        node = get_object_or_404(self.model, id=node_id)
        assets = node.get_all_assets()
        # task_name = _("测试节点下资产是否可连接: {}".format(node.name))
        task_name = _("Test if the assets under the node are connectable: {}".format(node.name))
        task = test_asset_connectivity_util.delay(assets, task_name=task_name)
        return Response({"task": task.id})


class RefreshNodesCacheApi(APIView):
    permission_classes = (IsOrgAdmin,)

    def get(self, request, *args, **kwargs):
        Node.refresh_nodes()
        return Response("Ok")

    def delete(self, *args, **kwargs):
        self.get(*args, **kwargs)
        return Response(status=204)
