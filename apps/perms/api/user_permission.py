# -*- coding: utf-8 -*-
#

from hashlib import md5
from django.core.cache import cache
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView, Response
from rest_framework.generics import (
    ListAPIView, get_object_or_404,
)
from rest_framework.pagination import LimitOffsetPagination

from common.permissions import IsValidUser, IsOrgAdminOrAppUser
from common.tree import TreeNodeSerializer
from common.utils import get_logger
from orgs.utils import set_to_root_org
from ..utils import (
    AssetPermissionUtil, parse_asset_to_tree_node, parse_node_to_tree_node,
    check_system_user_action, RemoteAppPermissionUtil,
    construct_remote_apps_tree_root, parse_remote_app_to_tree_node,
)
from ..hands import (
    User, Asset, Node, SystemUser, RemoteApp, AssetGrantedSerializer,
    NodeSerializer, RemoteAppSerializer,
)
from .. import serializers, const
from ..mixins import (
    AssetsFilterMixin, RemoteAppFilterMixin, ChangeOrgIfNeedMixin
)
from ..models import Action

logger = get_logger(__name__)

__all__ = [
    'UserGrantedAssetsApi', 'UserGrantedNodesApi',
    'UserGrantedNodesWithAssetsApi', 'UserGrantedNodeAssetsApi',
    'ValidateUserAssetPermissionApi', 'UserGrantedNodeChildrenApi',
    'UserGrantedNodesWithAssetsAsTreeApi', 'GetUserAssetPermissionActionsApi',
    'UserGrantedRemoteAppsApi', 'ValidateUserRemoteAppPermissionApi',
    'UserGrantedRemoteAppsAsTreeApi',
]


class UserPermissionCacheMixin:
    cache_policy = '0'
    RESP_CACHE_KEY = '_PERMISSION_RESPONSE_CACHE_{}'
    CACHE_TIME = settings.ASSETS_PERM_CACHE_TIME
    _object = None

    @staticmethod
    def change_org_if_need(request, kwargs):
        if request.user.is_authenticated and \
                request.user.is_superuser or \
                request.user.is_app or \
                kwargs.get('pk') is None:
            set_to_root_org()

    def get_object(self):
        return None

    # 内部使用可控制缓存
    def _get_object(self):
        if not self._object:
            self._object = self.get_object()
        return self._object

    def get_object_id(self):
        obj = self._get_object()
        if obj:
            return str(obj.id)
        return None

    def get_request_md5(self):
        full_path = self.request.get_full_path()
        return md5(full_path.encode()).hexdigest()

    def get_meta_cache_id(self):
        obj = self._get_object()
        util = AssetPermissionUtil(obj, cache_policy=self.cache_policy)
        meta_cache_id = util.cache_meta.get('id')
        return meta_cache_id

    def get_response_cache_id(self):
        obj_id = self.get_object_id()
        request_md5 = self.get_request_md5()
        meta_cache_id = self.get_meta_cache_id()
        resp_cache_id = '{}_{}_{}'.format(obj_id, request_md5, meta_cache_id)
        return resp_cache_id

    def get_response_from_cache(self):
        resp_cache_id = self.get_response_cache_id()
        # 没有数据缓冲
        meta_cache_id = self.get_meta_cache_id()
        if not meta_cache_id:
            return None
        # 从响应缓冲里获取响应
        key = self.RESP_CACHE_KEY.format(resp_cache_id)
        data = cache.get(key)
        if not data:
            return None
        logger.debug("Get user permission from cache: {}".format(self.get_object()))
        response = Response(data)
        return response

    def expire_response_cache(self):
        obj_id = self.get_object_id()
        expire_cache_id = '{}_{}'.format(obj_id, '*')
        key = self.RESP_CACHE_KEY.format(expire_cache_id)
        cache.delete_pattern(key)

    def set_response_to_cache(self, response):
        resp_cache_id = self.get_response_cache_id()
        key = self.RESP_CACHE_KEY.format(resp_cache_id)
        cache.set(key, response.data, self.CACHE_TIME)

    def get(self, request, *args, **kwargs):
        self.change_org_if_need(request, kwargs)
        self.cache_policy = request.GET.get('cache_policy', '0')

        obj = self._get_object()
        if obj is None:
            return super().get(request, *args, **kwargs)

        if AssetPermissionUtil.is_not_using_cache(self.cache_policy):
            return super().get(request, *args, **kwargs)
        elif AssetPermissionUtil.is_refresh_cache(self.cache_policy):
            self.expire_response_cache()

        resp = self.get_response_from_cache()
        if not resp:
            resp = super().get(request, *args, **kwargs)
            self.set_response_to_cache(resp)
        return resp


class UserGrantedAssetsApi(UserPermissionCacheMixin, AssetsFilterMixin, ListAPIView):
    """
    用户授权的所有资产
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = AssetGrantedSerializer
    pagination_class = LimitOffsetPagination

    def get_object(self):
        user_id = self.kwargs.get('pk', '')
        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user
        return user

    def get_queryset(self):
        queryset = []
        user = self.get_object()
        util = AssetPermissionUtil(user, cache_policy=self.cache_policy)
        assets = util.get_assets()
        for k, v in assets.items():
            system_users_granted = [s for s in v if s.protocol == k.protocol]
            k.system_users_granted = system_users_granted
            queryset.append(k)
        return queryset

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGrantedNodesApi(UserPermissionCacheMixin, ListAPIView):
    """
    查询用户授权的所有节点的API, 如果是超级用户或者是 app，切换到root org
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = NodeSerializer

    def get_object(self):
        user_id = self.kwargs.get('pk', '')
        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user
        return user

    def get_queryset(self):
        user = self.get_object()
        util = AssetPermissionUtil(user, cache_policy=self.cache_policy)
        nodes = util.get_nodes_with_assets()
        return nodes.keys()

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGrantedNodesWithAssetsApi(UserPermissionCacheMixin, AssetsFilterMixin, ListAPIView):
    """
    用户授权的节点并带着节点下资产的api
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.NodeGrantedSerializer

    def get_object(self):
        user_id = self.kwargs.get('pk', '')
        if not user_id:
            user = self.request.user
        else:
            user = get_object_or_404(User, id=user_id)
        return user

    def get_queryset(self):
        queryset = []
        user = self.get_object()
        util = AssetPermissionUtil(user, cache_policy=self.cache_policy)
        nodes = util.get_nodes_with_assets()
        for node, _assets in nodes.items():
            assets = _assets.keys()
            for k, v in _assets.items():
                system_users_granted = [s for s in v if
                                        s.protocol == k.protocol]
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


class UserGrantedNodesWithAssetsAsTreeApi(UserPermissionCacheMixin, ListAPIView):
    serializer_class = TreeNodeSerializer
    permission_classes = (IsOrgAdminOrAppUser,)
    show_assets = True
    system_user_id = None

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()

    def get_object(self):
        user_id = self.kwargs.get('pk', '')
        if not user_id:
            user = self.request.user
        else:
            user = get_object_or_404(User, id=user_id)
        return user

    def list(self, request, *args, **kwargs):
        resp = super().list(request, *args, **kwargs)
        return resp

    def get_queryset(self):
        queryset = []
        self.show_assets = self.request.query_params.get('show_assets', '1') == '1'
        self.system_user_id = self.request.query_params.get('system_user')
        user = self.get_object()
        util = AssetPermissionUtil(user, cache_policy=self.cache_policy)
        if self.system_user_id:
            util.filter_permissions(
                system_users=self.system_user_id
            )
        nodes = util.get_nodes_with_assets()
        for node, assets in nodes.items():
            data = parse_node_to_tree_node(node)
            queryset.append(data)
            if not self.show_assets:
                continue
            for asset, system_users in assets.items():
                data = parse_asset_to_tree_node(node, asset, system_users)
                queryset.append(data)
        queryset = sorted(queryset)
        return queryset


class UserGrantedNodeAssetsApi(UserPermissionCacheMixin, AssetsFilterMixin, ListAPIView):
    """
    查询用户授权的节点下的资产的api, 与上面api不同的是，只返回某个节点下的资产
    """
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = AssetGrantedSerializer
    pagination_class = LimitOffsetPagination

    def get_object(self):
        user_id = self.kwargs.get('pk', '')

        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user
        return user

    def get_queryset(self):
        user = self.get_object()
        node_id = self.kwargs.get('node_id')
        util = AssetPermissionUtil(user, cache_policy=self.cache_policy)
        if str(node_id) == const.UNGROUPED_NODE_ID:
            node = util.tree.ungrouped_node
        else:
            node = get_object_or_404(Node, id=node_id)
        if node == util.tree.root_node:
            assets = util.get_assets()
        else:
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


class UserGrantedNodeChildrenApi(UserPermissionCacheMixin, ListAPIView):
    """
    获取用户自己授权节点下子节点的api
    """
    permission_classes = (IsValidUser,)
    serializer_class = serializers.AssetPermissionNodeSerializer

    def get_object(self):
        return self.request.user

    def get_children_queryset(self):
        user = self.get_object()
        util = AssetPermissionUtil(user, cache_policy=self.cache_policy)
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
        user = self.get_object()
        util = AssetPermissionUtil(user, cache_policy=self.cache_policy)
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
        keyword = self.request.query_params.get('search')
        if keyword:
            return self.get_search_queryset(keyword)
        else:
            return self.get_children_queryset()


class ValidateUserAssetPermissionApi(UserPermissionCacheMixin, APIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    def get(self, request, *args, **kwargs):
        user_id = request.query_params.get('user_id', '')
        asset_id = request.query_params.get('asset_id', '')
        system_id = request.query_params.get('system_user_id', '')
        action_name = request.query_params.get('action_name', '')

        user = get_object_or_404(User, id=user_id)
        asset = get_object_or_404(Asset, id=asset_id)
        su = get_object_or_404(SystemUser, id=system_id)
        action = get_object_or_404(Action, name=action_name)

        util = AssetPermissionUtil(user, cache_policy=self.cache_policy)
        granted_assets = util.get_assets()
        granted_system_users = granted_assets.get(asset, [])

        if su not in granted_system_users:
            return Response({'msg': False}, status=403)

        _su = next((s for s in granted_system_users if s.id == su.id), None)
        if not check_system_user_action(_su, action):
            return Response({'msg': False}, status=403)

        return Response({'msg': True}, status=200)


class GetUserAssetPermissionActionsApi(UserPermissionCacheMixin, APIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    def get(self, request, *args, **kwargs):
        user_id = request.query_params.get('user_id', '')
        asset_id = request.query_params.get('asset_id', '')
        system_id = request.query_params.get('system_user_id', '')

        user = get_object_or_404(User, id=user_id)
        asset = get_object_or_404(Asset, id=asset_id)
        su = get_object_or_404(SystemUser, id=system_id)

        util = AssetPermissionUtil(user, cache_policy=self.cache_policy)
        granted_assets = util.get_assets()
        granted_system_users = granted_assets.get(asset, [])
        _su = next((s for s in granted_system_users if s.id == su.id), None)
        if not _su:
            return Response({'actions': []}, status=403)

        actions = [action.name for action in getattr(_su, 'actions', [])]
        return Response({'actions': actions}, status=200)


# RemoteApp permission

class UserGrantedRemoteAppsApi(ChangeOrgIfNeedMixin, RemoteAppFilterMixin, ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = RemoteAppSerializer
    pagination_class = LimitOffsetPagination

    def get_object(self):
        user_id = self.kwargs.get('pk', '')
        if user_id:
            user = get_object_or_404(User, id=user_id)
        else:
            user = self.request.user
        return user

    def get_queryset(self):
        util = RemoteAppPermissionUtil(self.get_object())
        queryset = util.get_remote_apps()
        queryset = list(queryset)
        return queryset

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class UserGrantedRemoteAppsAsTreeApi(ChangeOrgIfNeedMixin, ListAPIView):
    serializer_class = TreeNodeSerializer
    permission_classes = (IsOrgAdminOrAppUser,)

    def get_object(self):
        user_id = self.kwargs.get('pk', '')
        if not user_id:
            user = self.request.user
        else:
            user = get_object_or_404(User, id=user_id)
        return user

    def get_queryset(self):
        queryset = []
        tree_root = construct_remote_apps_tree_root()
        queryset.append(tree_root)

        util = RemoteAppPermissionUtil(self.get_object())
        remote_apps = util.get_remote_apps()
        for remote_app in remote_apps:
            node = parse_remote_app_to_tree_node(tree_root, remote_app)
            queryset.append(node)

        queryset = sorted(queryset)
        return queryset

    def get_permissions(self):
        if self.kwargs.get('pk') is None:
            self.permission_classes = (IsValidUser,)
        return super().get_permissions()


class ValidateUserRemoteAppPermissionApi(ChangeOrgIfNeedMixin, APIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    def get(self, request, *args, **kwargs):
        self.change_org_if_need(request, kwargs)
        user_id = request.query_params.get('user_id', '')
        remote_app_id = request.query_params.get('remote_app_id', '')
        user = get_object_or_404(User, id=user_id)
        remote_app = get_object_or_404(RemoteApp, id=remote_app_id)

        util = RemoteAppPermissionUtil(user)
        remote_apps = util.get_remote_apps()
        if remote_app not in remote_apps:
            return Response({'msg': False}, status=403)

        return Response({'msg': True}, status=200)
