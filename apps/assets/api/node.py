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

from rest_framework import generics, mixins
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_bulk import BulkModelViewSet
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404

from common.utils import get_logger, get_object_or_none
from ..hands import IsSuperUser
from ..models import Node
from ..tasks import update_assets_hardware_info_util, test_asset_connectability_util
from .. import serializers


logger = get_logger(__file__)
__all__ = [
    'NodeViewSet', 'NodeChildrenApi',
    'NodeAssetsApi', 'NodeWithAssetsApi',
    'NodeAddAssetsApi', 'NodeRemoveAssetsApi',
    'NodeReplaceAssetsApi',
    'NodeAddChildrenApi', 'RefreshNodeHardwareInfoApi',
    'TestNodeConnectiveApi'
]


class NodeViewSet(BulkModelViewSet):
    queryset = Node.objects.all()
    permission_classes = (IsSuperUser,)
    serializer_class = serializers.NodeSerializer

    def perform_create(self, serializer):
        child_key = Node.root().get_next_child_key()
        serializer.validated_data["key"] = child_key
        serializer.save()


class NodeWithAssetsApi(generics.ListAPIView):
    permission_classes = (IsSuperUser,)
    serializers = serializers.NodeSerializer

    def get_node(self):
        pk = self.kwargs.get('pk') or self.request.query_params.get('node')
        if not pk:
            node = Node.root()
        else:
            node = get_object_or_404(Node, pk)
        return node

    def get_queryset(self):
        queryset = []
        node = self.get_node()
        children = node.get_children()
        assets = node.get_assets()
        queryset.extend(list(children))

        for asset in assets:
            node = Node()
            node.id = asset.id
            node.parent = node.id
            node.value = asset.hostname
            queryset.append(node)
        return queryset


class NodeChildrenApi(mixins.ListModelMixin, generics.CreateAPIView):
    queryset = Node.objects.all()
    permission_classes = (IsSuperUser,)
    serializer_class = serializers.NodeSerializer
    instance = None

    def post(self, request, *args, **kwargs):
        if not request.data.get("value"):
            request.data["value"] = _("New node {}").format(
                Node.root().get_next_child_key().split(":")[-1]
            )
        return super().post(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        instance = self.get_object()
        value = request.data.get("value")
        node = instance.create_child(value=value)
        return Response(
            {"id": node.id, "key": node.key, "value": node.value},
            status=201,
        )

    def get_object(self):
        pk = self.kwargs.get('pk') or self.request.query_params.get('id')
        if not pk:
            node = Node.root()
        else:
            node = get_object_or_404(Node, pk=pk)
        return node

    def get_queryset(self):
        queryset = []
        query_all = self.request.query_params.get("all")
        query_assets = self.request.query_params.get('assets')
        node = self.get_object()
        if node == Node.root():
            queryset.append(node)
        if query_all:
            children = node.get_all_children()
        else:
            children = node.get_children()

        queryset.extend(list(children))
        if query_assets:
            assets = node.get_assets()
            for asset in assets:
                node_fake = Node()
                node_fake.id = asset.id
                node_fake.parent = node
                node_fake.value = asset.hostname
                node_fake.is_asset = True
                queryset.append(node_fake)
        return queryset

    def get(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class NodeAssetsApi(generics.ListAPIView):
    permission_classes = (IsSuperUser,)
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
    queryset = Node.objects.all()
    permission_classes = (IsSuperUser,)
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
            node.save()
        return Response("OK")


class NodeAddAssetsApi(generics.UpdateAPIView):
    serializer_class = serializers.NodeAssetsSerializer
    queryset = Node.objects.all()
    permission_classes = (IsSuperUser,)
    instance = None

    def perform_update(self, serializer):
        assets = serializer.validated_data.get('assets')
        instance = self.get_object()
        instance.assets.add(*tuple(assets))


class NodeRemoveAssetsApi(generics.UpdateAPIView):
    serializer_class = serializers.NodeAssetsSerializer
    queryset = Node.objects.all()
    permission_classes = (IsSuperUser,)
    instance = None

    def perform_update(self, serializer):
        assets = serializer.validated_data.get('assets')
        instance = self.get_object()
        if instance != Node.root():
            instance.assets.remove(*tuple(assets))


class NodeReplaceAssetsApi(generics.UpdateAPIView):
    serializer_class = serializers.NodeAssetsSerializer
    queryset = Node.objects.all()
    permission_classes = (IsSuperUser,)
    instance = None

    def perform_update(self, serializer):
        assets = serializer.validated_data.get('assets')
        instance = self.get_object()
        for asset in assets:
            asset.nodes.set([instance])


class RefreshNodeHardwareInfoApi(APIView):
    permission_classes = (IsSuperUser,)
    model = Node

    def get(self, request, *args, **kwargs):
        node_id = kwargs.get('pk')
        node = get_object_or_404(self.model, id=node_id)
        assets = node.assets.all()
        task_name = _("更新节点资产硬件信息: {}".format(node.name))
        task = update_assets_hardware_info_util.delay(assets, task_name=task_name)
        return Response({"task": task.id})


class TestNodeConnectiveApi(APIView):
    permission_classes = (IsSuperUser,)
    model = Node

    def get(self, request, *args, **kwargs):
        node_id = kwargs.get('pk')
        node = get_object_or_404(self.model, id=node_id)
        assets = node.assets.all()
        task_name = _("测试节点下资产是否可连接: {}".format(node.name))
        task = test_asset_connectability_util.delay(assets, task_name=task_name)
        return Response({"task": task.id})
