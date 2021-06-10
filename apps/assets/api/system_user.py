# ~*~ coding: utf-8 ~*~
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from common.utils import get_logger
from common.permissions import IsOrgAdmin, IsOrgAdminOrAppUser, IsValidUser
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.mixins import generics
from orgs.utils import tmp_to_root_org
from ..models import SystemUser, Asset
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


class SystemUserViewSet(OrgBulkModelViewSet):
    """
    System user api set, for add,delete,update,list,retrieve resource
    """
    model = SystemUser
    filterset_fields = {
        'name': ['exact'],
        'username': ['exact'],
        'protocol': ['exact', 'in']
    }
    search_fields = filterset_fields
    serializer_class = serializers.SystemUserSerializer
    serializer_classes = {
        'default': serializers.SystemUserSerializer,
        'list': serializers.SystemUserListSerializer,
    }
    permission_classes = (IsOrgAdminOrAppUser,)


class SystemUserAuthInfoApi(generics.RetrieveUpdateDestroyAPIView):
    """
    Get system user auth info
    """
    model = SystemUser
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = SystemUserWithAuthInfoSerializer

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
        user = self.request.user
        data = serializer.validated_data
        instance_id = data.get('instance_id')

        with tmp_to_root_org():
            instance = get_object_or_404(SystemUser, pk=pk)
            instance.set_temp_auth(instance_id, user, data)
        return Response(serializer.data, status=201)


class SystemUserAssetAuthInfoApi(generics.RetrieveAPIView):
    """
    Get system user with asset auth info
    """
    model = SystemUser
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = SystemUserWithAuthInfoSerializer

    def get_object(self):
        instance = super().get_object()
        asset_id = self.kwargs.get('asset_id')
        user_id = self.request.query_params.get("user_id")
        username = self.request.query_params.get("username")
        instance.load_asset_more_auth(asset_id=asset_id, user_id=user_id, username=username)
        return instance


class SystemUserAppAuthInfoApi(generics.RetrieveAPIView):
    """
    Get system user with asset auth info
    """
    model = SystemUser
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = SystemUserWithAuthInfoSerializer

    def get_object(self):
        instance = super().get_object()
        app_id = self.kwargs.get('app_id')
        user_id = self.request.query_params.get("user_id")
        if user_id:
            instance.load_app_more_auth(app_id, user_id)
        return instance


class SystemUserTaskApi(generics.CreateAPIView):
    permission_classes = (IsOrgAdmin,)
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
    permission_classes = (IsOrgAdminOrAppUser,)

    def get_serializer_class(self):
        from ..serializers import CommandFilterRuleSerializer
        return CommandFilterRuleSerializer

    def get_queryset(self):
        pk = self.kwargs.get('pk', None)
        system_user = get_object_or_404(SystemUser, pk=pk)
        return system_user.cmd_filter_rules


class SystemUserAssetsListView(generics.ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetSimpleSerializer
    filterset_fields = ("hostname", "ip")
    search_fields = filterset_fields

    def get_object(self):
        pk = self.kwargs.get('pk')
        return get_object_or_404(SystemUser, pk=pk)

    def get_queryset(self):
        system_user = self.get_object()
        return system_user.get_all_assets()
