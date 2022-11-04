# ~*~ coding: utf-8 ~*~
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.decorators import action

from common.utils import get_logger, get_object_or_none
from common.permissions import IsValidUser
from common.mixins.api import SuggestionMixin
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.mixins import generics
from orgs.utils import tmp_to_root_org
from ..models import SystemUser, CommandFilterRule
from .. import serializers
from ..serializers import SystemUserWithAuthInfoSerializer, SystemUserTempAuthSerializer
from ..tasks import (
    push_system_user_to_assets_manual, test_system_user_connectivity_manual,
    push_system_user_to_assets
)

logger = get_logger(__file__)
__all__ = [
    'SystemUserViewSet', 'SystemUserAuthInfoApi', 'SystemUserAssetAuthInfoApi',
    'SystemUserCommandFilterRuleListApi', 'SystemUserTaskApi', 'SystemUserAssetsListView',
    'SystemUserTempAuthInfoApi', 'SystemUserAppAuthInfoApi',
]


class SystemUserViewSet(SuggestionMixin, OrgBulkModelViewSet):
    """
    System user api set, for add,delete,update,list,retrieve resource
    """
    model = SystemUser
    filterset_fields = {
        'name': ['exact'],
        'username': ['exact'],
        'protocol': ['exact', 'in'],
        'type': ['exact', 'in'],
    }
    search_fields = filterset_fields
    serializer_class = serializers.SystemUserSerializer
    serializer_classes = {
        'default': serializers.SystemUserSerializer,
        'suggestion': serializers.MiniSystemUserSerializer
    }
    ordering_fields = ('name', 'protocol', 'login_mode')
    ordering = ('name', )
    rbac_perms = {
        'su_from': 'assets.view_systemuser',
        'su_to': 'assets.view_systemuser',
        'match': 'assets.match_systemuser'
    }

    @action(methods=['get'], detail=False, url_path='su-from')
    def su_from(self, request, *args, **kwargs):
        """ API 获取可选的 su_from 系统用户"""
        queryset = self.filter_queryset(self.get_queryset())
        queryset = queryset.filter(
            protocol=SystemUser.Protocol.ssh, login_mode=SystemUser.LOGIN_AUTO
        )
        return self.get_paginate_response_if_need(queryset)

    @action(methods=['get'], detail=True, url_path='su-to')
    def su_to(self, request, *args, **kwargs):
        """ 获取系统用户的所有 su_to 系统用户 """
        pk = kwargs.get('pk')
        system_user = get_object_or_404(SystemUser, pk=pk)
        queryset = system_user.su_to.all()
        queryset = self.filter_queryset(queryset)
        return self.get_paginate_response_if_need(queryset)

    def get_paginate_response_if_need(self, queryset):
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class SystemUserAuthInfoApi(generics.RetrieveUpdateDestroyAPIView):
    """
    Get system user auth info
    """
    model = SystemUser
    serializer_class = SystemUserWithAuthInfoSerializer
    rbac_perms = {
        'retrieve': 'assets.view_systemusersecret',
        'list': 'assets.view_systemusersecret',
        'change': 'assets.change_systemuser',
        'destroy': 'assets.change_systemuser',
    }

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.clear_auth()
        return Response(status=204)


class SystemUserTempAuthInfoApi(generics.CreateAPIView):
    model = SystemUser
    permission_classes = (IsValidUser,)
    serializer_class = SystemUserTempAuthSerializer

    def create(self, request, *args, **kwargs):
        serializer = super().get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pk = kwargs.get('pk')
        data = serializer.validated_data
        asset_or_app_id = data.get('instance_id')

        with tmp_to_root_org():
            instance = get_object_or_404(SystemUser, pk=pk)
            instance.set_temp_auth(asset_or_app_id, self.request.user.id, data)
        return Response(serializer.data, status=201)


class SystemUserAssetAuthInfoApi(generics.RetrieveAPIView):
    """
    Get system user with asset auth info
    """
    model = SystemUser
    serializer_class = SystemUserWithAuthInfoSerializer

    def get_object(self):
        instance = super().get_object()
        asset_id = self.kwargs.get('asset_id')
        user_id = self.request.query_params.get("user_id")
        username = self.request.query_params.get("username")
        instance.load_asset_more_auth(asset_id, username, user_id)
        return instance


class SystemUserAppAuthInfoApi(generics.RetrieveAPIView):
    """
    Get system user with asset auth info
    """
    model = SystemUser
    serializer_class = SystemUserWithAuthInfoSerializer
    rbac_perms = {
        'retrieve': 'assets.view_systemusersecret',
    }

    def get_object(self):
        instance = super().get_object()
        app_id = self.kwargs.get('app_id')
        user_id = self.request.query_params.get("user_id")
        username = self.request.query_params.get("username")
        instance.load_app_more_auth(app_id, username, user_id)
        return instance


class SystemUserTaskApi(generics.CreateAPIView):
    serializer_class = serializers.SystemUserTaskSerializer

    def do_push(self, system_user, asset_ids=None):
        if asset_ids is None:
            task = push_system_user_to_assets_manual.delay(system_user)
        else:
            username = self.request.query_params.get('username')
            task = push_system_user_to_assets.delay(
                system_user.id, asset_ids, username=username
            )
        return task

    @staticmethod
    def do_test(system_user, asset_ids):
        task = test_system_user_connectivity_manual.delay(system_user, asset_ids)
        return task

    def get_object(self):
        pk = self.kwargs.get('pk')
        return get_object_or_404(SystemUser, pk=pk)

    def check_permissions(self, request):
        action = request.data.get('action')
        action_perm_require = {
            'push': 'assets.push_assetsystemuser',
            'test': 'assets.test_assetconnectivity'
        }
        perm_required = action_perm_require.get(action)
        has = self.request.user.has_perm(perm_required)

        if not has:
            self.permission_denied(request)

    def perform_create(self, serializer):
        action = serializer.validated_data["action"]
        asset = serializer.validated_data.get('asset')

        if asset:
            assets = [asset]
        else:
            assets = serializer.validated_data.get('assets') or []

        asset_ids = [asset.id for asset in assets]
        asset_ids = asset_ids if asset_ids else None

        system_user = self.get_object()
        if action == 'push':
            task = self.do_push(system_user, asset_ids)
        else:
            task = self.do_test(system_user, asset_ids)
        data = getattr(serializer, '_data', {})
        data["task"] = task.id
        setattr(serializer, '_data', data)


class SystemUserCommandFilterRuleListApi(generics.ListAPIView):
    rbac_perms = {
        'list': 'assets.view_commandfilterule',
    }

    def get_serializer_class(self):
        from ..serializers import CommandFilterRuleSerializer
        return CommandFilterRuleSerializer

    def get_queryset(self):
        user_id = self.request.query_params.get('user_id')
        user_group_id = self.request.query_params.get('user_group_id')
        system_user_id = self.kwargs.get('pk', None)
        system_user = get_object_or_none(SystemUser, pk=system_user_id)
        if not system_user:
            system_user_id = self.request.query_params.get('system_user_id')
        asset_id = self.request.query_params.get('asset_id')
        node_id = self.request.query_params.get('node_id')
        application_id = self.request.query_params.get('application_id')
        rules = CommandFilterRule.get_queryset(
            user_id=user_id,
            user_group_id=user_group_id,
            system_user_id=system_user_id,
            asset_id=asset_id,
            node_id=node_id,
            application_id=application_id
        )
        return rules


class SystemUserAssetsListView(generics.ListAPIView):
    serializer_class = serializers.AssetSimpleSerializer
    filterset_fields = ("hostname", "ip")
    search_fields = filterset_fields
    rbac_perms = {
        'list': 'assets.view_asset'
    }

    def get_object(self):
        pk = self.kwargs.get('pk')
        return get_object_or_404(SystemUser, pk=pk)

    def get_queryset(self):
        system_user = self.get_object()
        return system_user.get_all_assets()
