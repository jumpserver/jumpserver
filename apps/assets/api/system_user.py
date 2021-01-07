# ~*~ coding: utf-8 ~*~
from django.shortcuts import get_object_or_404
from rest_framework.response import Response

from common.utils import get_logger
from common.permissions import IsOrgAdmin, IsOrgAdminOrAppUser
from common.drf.filters import CustomFilter
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.mixins import generics
from orgs.utils import tmp_to_org
from ..models import SystemUser, Asset
from .. import serializers
from ..serializers import SystemUserWithAuthInfoSerializer
from ..tasks import (
    push_system_user_to_assets_manual, test_system_user_connectivity_manual,
    push_system_user_to_assets
)


logger = get_logger(__file__)
__all__ = [
    'SystemUserViewSet', 'SystemUserAuthInfoApi', 'SystemUserAssetAuthInfoApi',
    'SystemUserCommandFilterRuleListApi', 'SystemUserTaskApi', 'SystemUserAssetsListView',
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


class SystemUserAssetAuthInfoApi(generics.RetrieveAPIView):
    """
    Get system user with asset auth info
    """
    model = SystemUser
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = SystemUserWithAuthInfoSerializer

    def get_exception_handler(self):
        def handler(e, context):
            return Response({"error": str(e)}, status=400)
        return handler

    def get_object(self):
        instance = super().get_object()
        username = instance.username
        if instance.username_same_with_user:
            username = self.request.query_params.get("username")
        asset_id = self.kwargs.get('aid')
        asset = get_object_or_404(Asset, pk=asset_id)

        with tmp_to_org(asset.org_id):
            instance.load_asset_special_auth(asset=asset, username=username)
            return instance


class SystemUserTaskApi(generics.CreateAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.SystemUserTaskSerializer

    def do_push(self, system_user, assets_id=None):
        if assets_id is None:
            task = push_system_user_to_assets_manual.delay(system_user)
        else:
            username = self.request.query_params.get('username')
            task = push_system_user_to_assets.delay(
                system_user.id, assets_id, username=username
            )
        return task

    @staticmethod
    def do_test(system_user):
        task = test_system_user_connectivity_manual.delay(system_user)
        return task

    def get_object(self):
        pk = self.kwargs.get('pk')
        return get_object_or_404(SystemUser, pk=pk)

    def perform_create(self, serializer):
        action = serializer.validated_data["action"]
        asset = serializer.validated_data.get('asset')
        assets = serializer.validated_data.get('assets') or []

        system_user = self.get_object()
        if action == 'push':
            assets = [asset] if asset else assets
            assets_id = [asset.id for asset in assets]
            assets_id = assets_id if assets_id else None
            task = self.do_push(system_user, assets_id)
        else:
            task = self.do_test(system_user)
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
