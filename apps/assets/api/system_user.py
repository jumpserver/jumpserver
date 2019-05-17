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

from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework_bulk import BulkModelViewSet
from rest_framework.pagination import LimitOffsetPagination

from common.utils import get_logger
from common.permissions import IsOrgAdmin, IsOrgAdminOrAppUser
from common.mixins import IDInCacheFilterMixin
from ..models import SystemUser, Asset
from .. import serializers
from ..tasks import push_system_user_to_assets_manual, \
    test_system_user_connectivity_manual, push_system_user_a_asset_manual, \
    test_system_user_connectivity_a_asset


logger = get_logger(__file__)
__all__ = [
    'SystemUserViewSet', 'SystemUserAuthInfoApi', 'SystemUserAssetAuthInfoApi',
    'SystemUserPushApi', 'SystemUserTestConnectiveApi',
    'SystemUserAssetsListView', 'SystemUserPushToAssetApi',
    'SystemUserTestAssetConnectivityApi', 'SystemUserCommandFilterRuleListApi',

]


class SystemUserViewSet(IDInCacheFilterMixin, BulkModelViewSet):
    """
    System user api set, for add,delete,update,list,retrieve resource
    """
    filter_fields = ("name", "username")
    search_fields = filter_fields
    queryset = SystemUser.objects.all()
    serializer_class = serializers.SystemUserSerializer
    permission_classes = (IsOrgAdminOrAppUser,)
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        queryset = super().get_queryset().all()
        return queryset


class SystemUserAuthInfoApi(generics.RetrieveUpdateDestroyAPIView):
    """
    Get system user auth info
    """
    queryset = SystemUser.objects.all()
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.SystemUserAuthSerializer

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.clear_auth()
        return Response(status=204)


class SystemUserAssetAuthInfoApi(generics.RetrieveAPIView):
    """
    Get system user with asset auth info
    """
    queryset = SystemUser.objects.all()
    permission_classes = (IsOrgAdminOrAppUser,)
    serializer_class = serializers.SystemUserAuthSerializer

    def get_object(self):
        instance = super().get_object()
        aid = self.kwargs.get('aid')
        asset = get_object_or_404(Asset, pk=aid)
        instance.load_specific_asset_auth(asset)
        return instance


class SystemUserPushApi(generics.RetrieveAPIView):
    """
    Push system user to cluster assets api
    """
    queryset = SystemUser.objects.all()
    permission_classes = (IsOrgAdmin,)

    def retrieve(self, request, *args, **kwargs):
        system_user = self.get_object()
        nodes = system_user.nodes.all()
        for node in nodes:
            system_user.assets.add(*tuple(node.get_all_assets()))
        task = push_system_user_to_assets_manual.delay(system_user)
        return Response({"task": task.id})


class SystemUserTestConnectiveApi(generics.RetrieveAPIView):
    """
    Push system user to cluster assets api
    """
    queryset = SystemUser.objects.all()
    permission_classes = (IsOrgAdmin,)

    def retrieve(self, request, *args, **kwargs):
        system_user = self.get_object()
        task = test_system_user_connectivity_manual.delay(system_user)
        return Response({"task": task.id})


class SystemUserAssetsListView(generics.ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetSimpleSerializer
    pagination_class = LimitOffsetPagination
    filter_fields = ("hostname", "ip")
    http_method_names = ['get']
    search_fields = filter_fields

    def get_object(self):
        pk = self.kwargs.get('pk')
        return get_object_or_404(SystemUser, pk=pk)

    def get_queryset(self):
        system_user = self.get_object()
        return system_user.assets.all()


class SystemUserPushToAssetApi(generics.RetrieveAPIView):
    queryset = SystemUser.objects.all()
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.TaskIDSerializer

    def retrieve(self, request, *args, **kwargs):
        system_user = self.get_object()
        asset_id = self.kwargs.get('aid')
        asset = get_object_or_404(Asset, id=asset_id)
        task = push_system_user_a_asset_manual.delay(system_user, asset)
        return Response({"task": task.id})


class SystemUserTestAssetConnectivityApi(generics.RetrieveAPIView):
    queryset = SystemUser.objects.all()
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.TaskIDSerializer

    def retrieve(self, request, *args, **kwargs):
        system_user = self.get_object()
        asset_id = self.kwargs.get('aid')
        asset = get_object_or_404(Asset, id=asset_id)
        task = test_system_user_connectivity_a_asset.delay(system_user, asset)
        return Response({"task": task.id})


class SystemUserCommandFilterRuleListApi(generics.ListAPIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    def get_serializer_class(self):
        from ..serializers import CommandFilterRuleSerializer
        return CommandFilterRuleSerializer

    def get_queryset(self):
        pk = self.kwargs.get('pk', None)
        system_user = get_object_or_404(SystemUser, pk=pk)
        return system_user.cmd_filter_rules
