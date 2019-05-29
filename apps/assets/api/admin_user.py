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

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework_bulk import BulkModelViewSet
from rest_framework.pagination import LimitOffsetPagination

from common.mixins import IDInCacheFilterMixin
from common.utils import get_logger
from ..hands import IsOrgAdmin
from ..models import AdminUser, Asset
from .. import serializers
from ..tasks import test_admin_user_connectivity_manual


logger = get_logger(__file__)
__all__ = [
    'AdminUserViewSet', 'ReplaceNodesAdminUserApi',
    'AdminUserTestConnectiveApi', 'AdminUserAuthApi',
    'AdminUserAssetsListView',
]


class AdminUserViewSet(IDInCacheFilterMixin, BulkModelViewSet):
    """
    Admin user api set, for add,delete,update,list,retrieve resource
    """

    filter_fields = ("name", "username")
    search_fields = filter_fields
    queryset = AdminUser.objects.all()
    serializer_class = serializers.AdminUserSerializer
    permission_classes = (IsOrgAdmin,)
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        queryset = super().get_queryset().all()
        return queryset


class AdminUserAuthApi(generics.UpdateAPIView):
    queryset = AdminUser.objects.all()
    serializer_class = serializers.AdminUserAuthSerializer
    permission_classes = (IsOrgAdmin,)


class ReplaceNodesAdminUserApi(generics.UpdateAPIView):
    queryset = AdminUser.objects.all()
    serializer_class = serializers.ReplaceNodeAdminUserSerializer
    permission_classes = (IsOrgAdmin,)

    def update(self, request, *args, **kwargs):
        admin_user = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            nodes = serializer.validated_data['nodes']
            assets = []
            for node in nodes:
                assets.extend([asset.id for asset in node.get_all_assets()])

            with transaction.atomic():
                Asset.objects.filter(id__in=assets).update(admin_user=admin_user)

            return Response({"msg": "ok"})
        else:
            return Response({'error': serializer.errors}, status=400)


class AdminUserTestConnectiveApi(generics.RetrieveAPIView):
    """
    Test asset admin user assets_connectivity
    """
    queryset = AdminUser.objects.all()
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.TaskIDSerializer

    def retrieve(self, request, *args, **kwargs):
        admin_user = self.get_object()
        task = test_admin_user_connectivity_manual.delay(admin_user)
        return Response({"task": task.id})


class AdminUserAssetsListView(generics.ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetSimpleSerializer
    pagination_class = LimitOffsetPagination
    filter_fields = ("hostname", "ip")
    http_method_names = ['get']
    search_fields = filter_fields

    def get_object(self):
        pk = self.kwargs.get('pk')
        return get_object_or_404(AdminUser, pk=pk)

    def get_queryset(self):
        admin_user = self.get_object()
        return admin_user.get_related_assets()
