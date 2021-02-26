# ~*~ coding: utf-8 ~*~
from functools import partial
from collections import namedtuple, defaultdict

from rest_framework import status
from rest_framework.serializers import ValidationError
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404, Http404
from django.db.models.signals import m2m_changed

from common.const.http import POST
from common.exceptions import SomeoneIsDoingThis
from common.const.signals import PRE_REMOVE, POST_REMOVE
from assets.models import Asset
from common.utils import get_logger, get_object_or_none
from common.tree import TreeNodeSerializer
from orgs.mixins.api import OrgModelViewSet
from orgs.mixins import generics
from orgs.utils import current_org
from ..hands import IsOrgAdmin
from ..models import Node
from ..tasks import (
    update_node_assets_hardware_info_manual,
    test_node_assets_connectivity_manual,
    check_node_assets_amount_task
)
from .. import serializers
from .mixin import SerializeToTreeNodeMixin


logger = get_logger(__file__)
__all__ = [
    'NodeViewSet', 'NodeChildrenApi', 'NodeAssetsApi',
    'NodeAddAssetsApi', 'NodeRemoveAssetsApi', 'MoveAssetsToNodeApi',
    'NodeAddChildrenApi', 'NodeListAsTreeApi',
    'NodeChildrenAsTreeApi',
    'NodeTaskCreateApi',
]


class NodeViewSet(OrgModelViewSet):
    model = Node
    filterset_fields = ('value', 'key', 'id')
    search_fields = ('value', )
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.NodeSerializer

    # 仅支持根节点指直接创建，子节点下的节点需要通过children接口创建
    def perform_create(self, serializer):
        child_key = Node.org_root().get_next_child_key()
        serializer.validated_data["key"] = child_key
        serializer.save()

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
        if node.has_children_or_has_assets():
            error = _("Deletion failed and the node contains children or assets")
            return Response(data={'error': error}, status=status.HTTP_403_FORBIDDEN)
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


class NodeChildrenAsTreeApi(SerializeToTreeNodeMixin, NodeChildrenApi):
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

    def list(self, request, *args, **kwargs):
        nodes = self.get_queryset().order_by('value')
        nodes = self.serialize_nodes(nodes, with_asset_amount=True)
        assets = self.get_assets()
        data = [*nodes, *assets]
        return Response(data=data)

    def get_assets(self):
        include_assets = self.request.query_params.get('assets', '0') == '1'
        if not include_assets:
            return []
        assets = self.instance.get_assets().only(
            "id", "hostname", "ip", "os", "platform_id",
            "org_id", "protocols", "is_active",
        ).prefetch_related('platform')
        return self.serialize_assets(assets, self.instance.key)


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
        children = Node.objects.filter(id__in=nodes_id)
        for node in children:
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
        node = self.get_object()
        node.assets.remove(*assets)

        # 把孤儿资产添加到 root 节点
        orphan_assets = Asset.objects.filter(id__in=[a.id for a in assets], nodes__isnull=True).distinct()
        Node.org_root().assets.add(*orphan_assets)


class MoveAssetsToNodeApi(generics.UpdateAPIView):
    model = Node
    serializer_class = serializers.NodeAssetsSerializer
    permission_classes = (IsOrgAdmin,)
    instance = None

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
    model = Node
    serializer_class = serializers.NodeTaskSerializer
    permission_classes = (IsOrgAdmin,)

    def get_object(self):
        node_id = self.kwargs.get('pk')
        node = get_object_or_none(self.model, id=node_id)
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
        if node is None:
            raise Http404()
        if action == "refresh":
            task = update_node_assets_hardware_info_manual.delay(node)
        else:
            task = test_node_assets_connectivity_manual.delay(node)
        self.set_serializer_data(serializer, task)

