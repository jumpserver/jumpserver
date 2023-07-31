# ~*~ coding: utf-8 ~*~
from collections import namedtuple, defaultdict
from functools import partial

from django.db.models.signals import m2m_changed
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from assets.models import Asset
from common.api import SuggestionMixin
from common.const.http import POST
from common.const.signals import PRE_REMOVE, POST_REMOVE
from common.exceptions import SomeoneIsDoingThis
from common.utils import get_logger
from orgs.mixins import generics
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.utils import current_org
from rbac.permissions import RBACPermission
from .. import serializers
from ..models import Node
from ..tasks import (
    update_node_assets_hardware_info_manual,
    test_node_assets_connectivity_manual,
    check_node_assets_amount_task
)

logger = get_logger(__file__)
__all__ = [
    'NodeViewSet', 'NodeAssetsApi', 'NodeAddAssetsApi',
    'NodeRemoveAssetsApi', 'MoveAssetsToNodeApi',
    'NodeAddChildrenApi', 'NodeTaskCreateApi',
]


class NodeViewSet(SuggestionMixin, OrgBulkModelViewSet):
    model = Node
    filterset_fields = ('value', 'key', 'id')
    search_fields = ('full_value',)
    serializer_class = serializers.NodeSerializer
    rbac_perms = {
        'match': 'assets.match_node',
        'check_assets_amount_task': 'assets.change_node'
    }

    @action(methods=[POST], detail=False, url_path='check_assets_amount_task')
    def check_assets_amount_task(self, request):
        task = check_node_assets_amount_task.delay(current_org.id)
        return Response(data={'task': task.id})

    def perform_update(self, serializer):
        node = self.get_object()
        if node.is_org_root() and node.value != serializer.validated_data['value']:
            msg = _("You can't update the root node name")
            raise ValidationError({"error": msg})
        return super().perform_update(serializer)

    def destroy(self, request, *args, **kwargs):
        node = self.get_object()
        if node.is_org_root():
            error = _("You can't delete the root node ({})".format(node.value))
            return Response(data={'error': error}, status=status.HTTP_403_FORBIDDEN)
        if node.has_offspring_assets():
            error = _("Deletion failed and the node contains assets")
            return Response(data={'error': error}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)


class NodeAssetsApi(generics.ListAPIView):
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
    serializer_class = serializers.NodeAddChildrenSerializer
    instance = None

    def update(self, request, *args, **kwargs):
        """ 同时支持 put 和 patch 方法"""
        instance = self.get_object()
        node_ids = request.data.get("nodes")
        children = Node.objects.filter(id__in=node_ids)
        for node in children:
            node.parent = instance
        return Response("OK")


class NodeAddAssetsApi(generics.UpdateAPIView):
    model = Node
    serializer_class = serializers.NodeAssetsSerializer
    instance = None
    permission_classes = (RBACPermission,)
    rbac_perms = {
        'PUT': 'assets.change_assetnodes',
    }

    def perform_update(self, serializer):
        assets = serializer.validated_data.get('assets')
        instance = self.get_object()
        instance.assets.add(*tuple(assets))


class NodeRemoveAssetsApi(generics.UpdateAPIView):
    model = Node
    serializer_class = serializers.NodeAssetsSerializer
    instance = None
    permission_classes = (RBACPermission,)
    rbac_perms = {
        'PUT': 'assets.change_assetnodes',
    }

    def perform_update(self, serializer):
        assets = serializer.validated_data.get('assets')
        node = self.get_object()
        node.assets.remove(*assets)

        # 把孤儿资产添加到 root 节点
        orphan_assets = Asset.objects.filter(
            id__in=[a.id for a in assets],
            nodes__isnull=True
        ).distinct()
        Node.org_root().assets.add(*orphan_assets)


class MoveAssetsToNodeApi(generics.UpdateAPIView):
    model = Node
    serializer_class = serializers.NodeAssetsSerializer
    instance = None
    permission_classes = (RBACPermission,)
    rbac_perms = {
        'PUT': 'assets.change_assetnodes',
    }

    def perform_update(self, serializer):
        assets = serializer.validated_data.get('assets')
        node = self.get_object()
        self.remove_old_nodes(assets)
        node.assets.add(*assets)

    def remove_old_nodes(self, assets):
        m2m_model = Asset.nodes.through

        # 查询资产与节点关系表，查出要移动资产与节点的所有关系
        relates = m2m_model.objects.filter(asset__in=assets).values_list('asset_id', 'node_id')
        if relates:
            # 对关系以资产进行分组，用来发 `reverse=False` 信号
            asset_nodes_mapper = defaultdict(set)
            for asset_id, node_id in relates:
                asset_nodes_mapper[asset_id].add(node_id)

            # 组建一个资产 id -> Asset 的 mapper
            asset_mapper = {asset.id: asset for asset in assets}

            # 创建删除关系信号发送函数
            senders = []
            for asset_id, node_id_set in asset_nodes_mapper.items():
                senders.append(partial(m2m_changed.send, sender=m2m_model, instance=asset_mapper[asset_id],
                                       reverse=False, model=Node, pk_set=node_id_set))
            # 发送 pre 信号
            [sender(action=PRE_REMOVE) for sender in senders]
            num = len(relates)
            asset_ids, node_ids = zip(*relates)
            # 删除之前的关系
            rows, _i = m2m_model.objects.filter(asset_id__in=asset_ids, node_id__in=node_ids).delete()
            if rows != num:
                raise SomeoneIsDoingThis
            # 发送 post 信号
            [sender(action=POST_REMOVE) for sender in senders]


class NodeTaskCreateApi(generics.CreateAPIView):
    perm_model = Asset
    model = Node
    serializer_class = serializers.NodeTaskSerializer

    def check_permissions(self, request):
        action = request.data.get('action')
        action_perm_require = {
            'refresh': 'assets.refresh_assethardwareinfo',
            'test': 'assets.test_assetconnectivity'
        }
        perm_required = action_perm_require.get(action)
        has = self.request.user.has_perm(perm_required)

        if not has:
            self.permission_denied(request)

    def get_object(self):
        node_id = self.kwargs.get('pk')
        node = get_object_or_404(self.model, id=node_id)
        return node

    @staticmethod
    def set_serializer_data(s, task):
        data = getattr(s, '_data', {})
        data["task"] = task.id
        setattr(s, '_data', data)

    @staticmethod
    def refresh_nodes_cache():
        Task = namedtuple('Task', ['id'])
        task = Task(id="0")
        return task

    def perform_create(self, serializer):
        action = serializer.validated_data["action"]
        node = self.get_object()
        if action == "refresh_cache" and node is None:
            task = self.refresh_nodes_cache()
            self.set_serializer_data(serializer, task)
            return

        if action == "refresh":
            task = update_node_assets_hardware_info_manual(node)
        else:
            task = test_node_assets_connectivity_manual(node)
        self.set_serializer_data(serializer, task)
