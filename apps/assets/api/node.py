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

from common.utils import get_logger, get_object_or_none
from ..hands import IsSuperUser
from ..models import Node
from .. import serializers


logger = get_logger(__file__)
__all__ = [
    'NodeViewSet', 'NodeChildrenApi',
    'NodeAddAssetsApi', 'NodeRemoveAssetsApi',
    'NodeAddChildrenApi',
]


class NodeViewSet(BulkModelViewSet):
    queryset = Node.objects.all()
    permission_classes = (IsSuperUser,)
    serializer_class = serializers.NodeSerializer

    def perform_create(self, serializer):
        child_key = Node.root().get_next_child_key()
        serializer.validated_data["key"] = child_key
        serializer.save()


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

    def get(self, request, *args, **kwargs):
        instance = self.get_object()
        if self.request.query_params.get("all"):
            children = instance.get_all_children()
        else:
            children = instance.get_children()
        response = [{"id": node.id, "key": node.key, "value": node.value} for node in children]
        return Response(response, status=200)


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
