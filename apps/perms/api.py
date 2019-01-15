# ~*~ coding: utf-8 ~*~
# 

from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from rest_framework.views import APIView, Response
from rest_framework.generics import (
    ListAPIView, get_object_or_404, RetrieveUpdateAPIView
)
from rest_framework import viewsets
from rest_framework.pagination import LimitOffsetPagination

from common.permissions import IsValidUser, IsOrgAdmin, IsOrgAdminOrAppUser
from common.tree import TreeNode, TreeNodeSerializer
from common.utils import get_object_or_none
from orgs.mixins import RootOrgViewMixin
from orgs.utils import set_to_root_org
from .utils import AssetPermissionUtil
from .models import AssetPermission
from .hands import (
    AssetGrantedSerializer, User, UserGroup, Asset, Node,
    SystemUser, NodeSerializer
)
from . import serializers
from .mixins import AssetsFilterMixin


__all__ = [
    'AssetPermissionViewSet', 'UserGrantedAssetsApi', 'UserGrantedNodesApi',
    'UserGrantedNodesWithAssetsApi', 'UserGrantedNodeAssetsApi', 'UserGroupGrantedAssetsApi',
    'UserGroupGrantedNodesApi', 'UserGroupGrantedNodesWithAssetsApi', 'UserGroupGrantedNodeAssetsApi',
    'ValidateUserAssetPermissionApi', 'AssetPermissionRemoveUserApi', 'AssetPermissionAddUserApi',
    'AssetPermissionRemoveAssetApi', 'AssetPermissionAddAssetApi', 'UserGrantedNodeChildrenApi',
    'UserGrantedNodesWithAssetsAsTreeApi',
]


class AssetPermissionViewSet(viewsets.ModelViewSet):
    """
    资产授权列表的增删改查api
    """
    queryset = AssetPermission.objects.all()
    serializer_class = serializers.AssetPermissionCreateUpdateSerializer
    pagination_class = LimitOffsetPagination
    filter_fields = ['name']
    permission_classes = (IsOrgAdmin,)

    def get_serializer_class(self):
        if self.action in ("list", 'retrieve'):
            return serializers.AssetPermissionListSerializer
        return self.serializer_class

    def filter_valid(self, queryset):
        valid = self.request.query_params.get('is_valid', None)
        if valid is None:
            return queryset
        if valid in ['0', 'N', 'false', 'False']:
            valid = False
        else:
            valid = True
        now = timezone.now()
        if valid:
            queryset = queryset.filter(is_active=True).filter(
                date_start__lt=now, date_expired__gt=now,
            )
        else:
            queryset = queryset.filter(
                Q(is_active=False) |
                Q(date_start__gt=now) |
                Q(date_expired__lt=now)
            )
        return queryset

    def filter_system_user(self, queryset):
        system_user_id = self.request.query_params.get('system_user_id')
        system_user_name = self.request.query_params.get('system_user')
        if system_user_id:
            system_user = get_object_or_none(SystemUser, pk=system_user_id)
        elif system_user_name:
            system_user = get_object_or_none(SystemUser, name=system_user_name)
        else:
            return queryset
        if not system_user:
            return queryset.none()
        queryset = queryset.filter(system_users=system_user)
        return queryset

    def filter_node(self, queryset):
        node_id = self.request.query_params.get('node_id')
        node_name = self.request.query_params.get('node')
        if node_id:
            node = get_object_or_none(Node, pk=node_id)
        elif node_name:
            node = get_object_or_none(Node, name=node_name)
        else:
            return queryset
        if not node:
            return queryset.none()
        nodes = node.get_ancestor(with_self=True)
        queryset = queryset.filter(nodes__in=nodes)
        return queryset

    def filter_asset(self, queryset):
        asset_id = self.request.query_params.get('asset_id')
        hostname = self.request.query_params.get('hostname')
        ip = self.request.query_params.get('ip')
        if asset_id:
            assets = Asset.objects.filter(pk=asset_id)
        elif hostname:
            assets = Asset.objects.filter(hostname=hostname)
        elif ip:
            assets = Asset.objects.filter(ip=ip)
        else:
            return queryset
        if not assets:
            return queryset.none()
        inherit_nodes = set()
        for asset in assets:
            for node in asset.nodes.all():
                inherit_nodes.update(set(node.get_ancestor(with_self=True)))
        queryset = queryset.filter(Q(assets__in=assets) | Q(nodes__in=inherit_nodes))
        return queryset

    def filter_user(self, queryset):
        user_id = self.request.query_params.get('user_id')
        username = self.request.query_params.get('username')
        if user_id:
            user = get_object_or_none(User, pk=user_id)
        elif username:
            user = get_object_or_none(User, username=username)
        else:
            return queryset
        if not user:
            return queryset.none()

    def filter_user_group(self, queryset):
        user_group_id = self.request.query_params.get('user_group_id')
        user_group_name = self.request.query_params.get('user_group')
        if user_group_id:
            group = get_object_or_none(UserGroup, pk=user_group_id)
        elif user_group_name:
            group = get_object_or_none(UserGroup, name=user_group_name)
        else:
            return queryset
        if not group:
            return queryset.none()
        queryset = queryset.filter(user_groups=group)
        return queryset

    def filter_keyword(self, queryset):
        keyword = self.request.query_params.get('search')
        if not keyword:
            return queryset
        queryset = queryset.filter(name__icontains=keyword)
        return queryset

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = self.filter_valid(queryset)
        queryset = self.filter_keyword(queryset)
        queryset = self.filter_asset(queryset)
        queryset = self.filter_node(queryset)
        queryset = self.filter_system_user(queryset)
        queryset = self.filter_user_group(queryset)
        return queryset

    def get_queryset(self):
        return self.queryset.all()


class UserGrantedAssetsApi(AssetsFilterMixin, ListAPIView):
    """
    用户授权的所有资产
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = AssetGrantedSerializer
    pagination_class = LimitOffsetPagination
    
    def change_org_if_need(self):
        if self.request.user.is_superuser or \
                self.request.user.is_app or \
                self.kwargs.get('pk') is None:
            set_to_root_org()
    
    def get_queryset(self):
        self.change_org_if_need()
        user_id = self.kwargs.get('pk', '')
        queryset = []

        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user

        util = AssetPermissionUtil(user)
        for k, v in util.get_assets().items():
            system_users_granted = [s for s in v if s.protocol == k.protocol]
            k.system_users_granted = system_users_granted
            queryset.append(k)

        return queryset

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGrantedNodesApi(ListAPIView):
    """
    查询用户授权的所有节点的API, 如果是超级用户或者是 app，切换到root org
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = NodeSerializer
    
    def change_org_if_need(self):
        if self.request.user.is_superuser or \
                self.request.user.is_app or \
                self.kwargs.get('pk') is None:
            set_to_root_org()

    def get_queryset(self):
        self.change_org_if_need()
        user_id = self.kwargs.get('pk', '')
        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user
        util = AssetPermissionUtil(user)
        nodes = util.get_nodes_with_assets()
        return nodes.keys()

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGrantedNodesWithAssetsApi(AssetsFilterMixin, ListAPIView):
    """
    用户授权的节点并带着节点下资产的api
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.NodeGrantedSerializer
    
    def change_org_if_need(self):
        if self.request.user.is_superuser or \
                self.request.user.is_app or \
                self.kwargs.get('pk') is None:
            set_to_root_org()

    def get_queryset(self):
        self.change_org_if_need()
        user_id = self.kwargs.get('pk', '')
        queryset = []
        if not user_id:
            user = self.request.user
        else:
            user = get_object_or_404(User, id=user_id)

        util = AssetPermissionUtil(user)
        nodes = util.get_nodes_with_assets()
        for node, _assets in nodes.items():
            assets = _assets.keys()
            for k, v in _assets.items():
                system_users_granted = [s for s in v if s.protocol == k.protocol]
                k.system_users_granted = system_users_granted
            node.assets_granted = assets
            queryset.append(node)
        return queryset

    def sort_assets(self, queryset):
        for node in queryset:
            node.assets_granted = super().sort_assets(node.assets_granted)
        return queryset

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGrantedNodesWithAssetsAsTreeApi(ListAPIView):
    serializer_class = TreeNodeSerializer
    permission_classes = (IsOrgAdminOrAppUser,)
    show_assets = True
    system_user_id = None

    def change_org_if_need(self):
        if self.request.user.is_superuser or \
                self.request.user.is_app or \
                self.kwargs.get('pk') is None:
            set_to_root_org()

    def get(self, request, *args, **kwargs):
        self.show_assets = request.query_params.get('show_assets', '1') == '1'
        self.system_user_id = request.query_params.get('system_user')
        return super().get(request, *args, **kwargs)

    @staticmethod
    def parse_node_to_tree_node(node):
        name = '{} ({})'.format(node.value, node.assets_amount)
        node_serializer = serializers.GrantedNodeSerializer(node)
        data = {
            'id': node.key,
            'name': name,
            'title': name,
            'pId': node.parent_key,
            'isParent': True,
            'open': node.is_root(),
            'meta': {
                'node': node_serializer.data,
                'type': 'node'
            }
        }
        tree_node = TreeNode(**data)
        return tree_node

    @staticmethod
    def parse_asset_to_tree_node(node, asset, system_users):
        system_users_protocol_matched = [s for s in system_users if s.protocol == asset.protocol]
        icon_skin = 'file'
        if asset.platform.lower() == 'windows':
            icon_skin = 'windows'
        elif asset.platform.lower() == 'linux':
            icon_skin = 'linux'
        system_users = []
        for system_user in system_users_protocol_matched:
            system_users.append({
                'id': system_user.id,
                'name': system_user.name,
                'username': system_user.username,
                'protocol': system_user.protocol,
                'priority': system_user.priority,
                'login_mode': system_user.login_mode,
                'comment': system_user.comment,
            })
        data = {
            'id': str(asset.id),
            'name': asset.hostname,
            'title': asset.ip,
            'pId': node.key,
            'isParent': False,
            'open': False,
            'iconSkin': icon_skin,
            'meta': {
                'system_users': system_users,
                'type': 'asset',
                'asset': {
                    'id': asset.id,
                    'hostname': asset.hostname,
                    'ip': asset.ip,
                    'port': asset.port,
                    'protocol': asset.protocol,
                    'platform': asset.platform,
                    'domain': None if not asset.domain else asset.domain.id,
                    'is_active': asset.is_active,
                    'comment': asset.comment
                },
            }
        }
        tree_node = TreeNode(**data)
        return tree_node

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()

    def get_queryset(self):
        self.change_org_if_need()
        user_id = self.kwargs.get('pk', '')
        queryset = []
        if not user_id:
            user = self.request.user
        else:
            user = get_object_or_404(User, id=user_id)
        util = AssetPermissionUtil(user)
        if self.system_user_id:
            util.filter_permission_with_system_user(system_user=self.system_user_id)
        nodes = util.get_nodes_with_assets()
        for node, assets in nodes.items():
            data = self.parse_node_to_tree_node(node)
            queryset.append(data)
            if not self.show_assets:
                continue
            for asset, system_users in assets.items():
                data = self.parse_asset_to_tree_node(node, asset, system_users)
                queryset.append(data)
        queryset = sorted(queryset)
        return queryset


class UserGrantedNodeAssetsApi(AssetsFilterMixin, ListAPIView):
    """
    查询用户授权的节点下的资产的api, 与上面api不同的是，只返回某个节点下的资产
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = AssetGrantedSerializer
    pagination_class = LimitOffsetPagination

    def change_org_if_need(self):
        if self.request.user.is_superuser or \
                self.request.user.is_app or \
                self.kwargs.get('pk') is None:
            set_to_root_org()

    def get_queryset(self):
        self.change_org_if_need()
        user_id = self.kwargs.get('pk', '')
        node_id = self.kwargs.get('node_id')

        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user
        util = AssetPermissionUtil(user)
        node = get_object_or_404(Node, id=node_id)
        nodes = util.get_nodes_with_assets()
        assets = nodes.get(node, [])
        for asset, system_users in assets.items():
            asset.system_users_granted = system_users

        assets = list(assets.keys())
        return assets

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGroupGrantedAssetsApi(ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = AssetGrantedSerializer

    def get_queryset(self):
        user_group_id = self.kwargs.get('pk', '')
        queryset = []

        if not user_group_id:
            return queryset

        user_group = get_object_or_404(UserGroup, id=user_group_id)
        util = AssetPermissionUtil(user_group)
        assets = util.get_assets()
        for k, v in assets.items():
            k.system_users_granted = v
            queryset.append(k)
        return queryset


class UserGroupGrantedNodesApi(ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = NodeSerializer

    def get_queryset(self):
        group_id = self.kwargs.get('pk', '')
        queryset = []

        if group_id:
            group = get_object_or_404(UserGroup, id=group_id)
            util = AssetPermissionUtil(group)
            nodes = util.get_nodes_with_assets()
            return nodes.keys()
        return queryset


class UserGroupGrantedNodesWithAssetsApi(ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.NodeGrantedSerializer

    def get_queryset(self):
        user_group_id = self.kwargs.get('pk', '')
        queryset = []

        if not user_group_id:
            return queryset

        user_group = get_object_or_404(UserGroup, id=user_group_id)
        util = AssetPermissionUtil(user_group)
        nodes = util.get_nodes_with_assets()
        for node, _assets in nodes.items():
            assets = _assets.keys()
            for asset, system_users in _assets.items():
                asset.system_users_granted = system_users
            node.assets_granted = assets
            queryset.append(node)
        return queryset


class UserGroupGrantedNodeAssetsApi(ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = AssetGrantedSerializer

    def get_queryset(self):
        user_group_id = self.kwargs.get('pk', '')
        node_id = self.kwargs.get('node_id')

        user_group = get_object_or_404(UserGroup, id=user_group_id)
        node = get_object_or_404(Node, id=node_id)
        util = AssetPermissionUtil(user_group)
        nodes = util.get_nodes_with_assets()
        assets = nodes.get(node, [])
        for asset, system_users in assets.items():
            asset.system_users_granted = system_users
        return assets


class ValidateUserAssetPermissionApi(RootOrgViewMixin, APIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    @staticmethod
    def get(request):
        user_id = request.query_params.get('user_id', '')
        asset_id = request.query_params.get('asset_id', '')
        system_id = request.query_params.get('system_user_id', '')

        user = get_object_or_404(User, id=user_id)
        asset = get_object_or_404(Asset, id=asset_id)
        system_user = get_object_or_404(SystemUser, id=system_id)

        util = AssetPermissionUtil(user)
        assets_granted = util.get_assets()
        if system_user in assets_granted.get(asset, []):
            return Response({'msg': True}, status=200)
        else:
            return Response({'msg': False}, status=403)


class AssetPermissionRemoveUserApi(RetrieveUpdateAPIView):
    """
    将用户从授权中移除，Detail页面会调用
    """
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetPermissionUpdateUserSerializer
    queryset = AssetPermission.objects.all()

    def update(self, request, *args, **kwargs):
        perm = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            users = serializer.validated_data.get('users')
            if users:
                perm.users.remove(*tuple(users))
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})


class AssetPermissionAddUserApi(RetrieveUpdateAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetPermissionUpdateUserSerializer
    queryset = AssetPermission.objects.all()

    def update(self, request, *args, **kwargs):
        perm = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            users = serializer.validated_data.get('users')
            if users:
                perm.users.add(*tuple(users))
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})


class AssetPermissionRemoveAssetApi(RetrieveUpdateAPIView):
    """
    将用户从授权中移除，Detail页面会调用
    """
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetPermissionUpdateAssetSerializer
    queryset = AssetPermission.objects.all()

    def update(self, request, *args, **kwargs):
        perm = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            assets = serializer.validated_data.get('assets')
            if assets:
                perm.assets.remove(*tuple(assets))
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})


class AssetPermissionAddAssetApi(RetrieveUpdateAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetPermissionUpdateAssetSerializer
    queryset = AssetPermission.objects.all()

    def update(self, request, *args, **kwargs):
        perm = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            assets = serializer.validated_data.get('assets')
            if assets:
                perm.assets.add(*tuple(assets))
            return Response({"msg": "ok"})
        else:
            return Response({"error": serializer.errors})


class UserGrantedNodeChildrenApi(ListAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = serializers.AssetPermissionNodeSerializer

    def change_org_if_need(self):
        if self.request.user.is_superuser or \
                self.request.user.is_app or \
                self.kwargs.get('pk') is None:
            set_to_root_org()

    def get_children_queryset(self):
        util = AssetPermissionUtil(self.request.user)
        node_id = self.request.query_params.get('id')
        nodes_granted = util.get_nodes_with_assets()
        if not nodes_granted:
            return []
        root_nodes = [node for node in nodes_granted.keys() if node.is_root()]

        queryset = []
        if node_id and node_id in [str(node.id) for node in nodes_granted]:
            node = [node for node in nodes_granted if str(node.id) == node_id][0]
        elif len(root_nodes) == 1:
            node = root_nodes[0]
            node.assets_amount = len(nodes_granted[node])
            queryset.append(node)
        else:
            for node in root_nodes:
                node.assets_amount = len(nodes_granted[node])
                queryset.append(node)
            return queryset

        children = []
        for child in node.get_children():
            if child in nodes_granted:
                child.assets_amount = len(nodes_granted[node])
                children.append(child)
        children = sorted(children, key=lambda x: x.value)
        queryset.extend(children)
        fake_nodes = []
        for asset, system_users in nodes_granted[node].items():
            fake_node = asset.as_node()
            fake_node.assets_amount = 0
            system_users = [s for s in system_users if s.protocol == asset.protocol]
            fake_node.asset.system_users_granted = system_users
            fake_node.key = node.key + ':0'
            fake_nodes.append(fake_node)
        fake_nodes = sorted(fake_nodes, key=lambda x: x.value)
        queryset.extend(fake_nodes)
        return queryset

    def get_search_queryset(self, keyword):
        util = AssetPermissionUtil(self.request.user)
        nodes_granted = util.get_nodes_with_assets()
        queryset = []
        for node, assets in nodes_granted.items():
            matched_assets = []
            node_matched = node.value.lower().find(keyword.lower()) >= 0
            asset_has_matched = False
            for asset, system_users in assets.items():
                asset_matched = (asset.hostname.lower().find(keyword.lower()) >= 0) \
                                or (asset.ip.find(keyword.lower()) >= 0)
                if node_matched or asset_matched:
                    asset_has_matched = True
                    fake_node = asset.as_node()
                    fake_node.assets_amount = 0
                    system_users = [s for s in system_users if
                                    s.protocol == asset.protocol]
                    fake_node.asset.system_users_granted = system_users
                    fake_node.key = node.key + ':0'
                    matched_assets.append(fake_node)
            if asset_has_matched:
                node.assets_amount = len(matched_assets)
                queryset.append(node)
                queryset.extend(sorted(matched_assets, key=lambda x: x.value))
        return queryset

    def get_queryset(self):
        self.change_org_if_need()
        keyword = self.request.query_params.get('search')
        if keyword:
            return self.get_search_queryset(keyword)
        else:
            return self.get_children_queryset()
