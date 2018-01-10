# ~*~ coding: utf-8 ~*~
# Copyright (C) 2014-2017 Beijing DuiZhan Technology Co.,Ltd. All Rights Reserved.
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

from rest_framework import generics
from rest_framework.response import Response
from rest_framework_bulk import BulkModelViewSet
from rest_framework_bulk import ListBulkCreateUpdateDestroyAPIView
from django.shortcuts import get_object_or_404
from django.db.models import Q

from common.mixins import IDInFilterMixin
from common.utils import get_logger
from .hands import IsSuperUser, IsValidUser, IsSuperUserOrAppUser, \
    get_user_granted_assets
from .models import AssetGroup, Asset, Cluster, SystemUser, AdminUser
from . import serializers
from .tasks import update_asset_hardware_info_manual, test_admin_user_connectability_manual, \
    test_asset_connectability_manual, push_system_user_to_cluster_assets_manual, \
    test_system_user_connectability_manual


logger = get_logger(__file__)


class AssetViewSet(IDInFilterMixin, BulkModelViewSet):
    """
    API endpoint that allows Asset to be viewed or edited.
    """
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetSerializer
    permission_classes = (IsSuperUserOrAppUser,)

    def get_queryset(self):
        queryset = super().get_queryset()
        cluster_id = self.request.query_params.get('cluster_id')
        asset_group_id = self.request.query_params.get('asset_group_id')
        admin_user_id = self.request.query_params.get('admin_user_id')
        system_user_id = self.request.query_params.get('system_user_id')

        if cluster_id:
            queryset = queryset.filter(cluster__id=cluster_id)
        if asset_group_id:
            queryset = queryset.filter(groups__id=asset_group_id)
        if admin_user_id:
            admin_user = get_object_or_404(AdminUser, id=admin_user_id)
            assets_direct = [asset.id for asset in admin_user.asset_set.all()]
            clusters = [cluster.id for cluster in admin_user.cluster_set.all()]
            queryset = queryset.filter(Q(cluster__id__in=clusters)|Q(id__in=assets_direct))
        if system_user_id:
            system_user = get_object_or_404(SystemUser, id=system_user_id)
            clusters = system_user.get_clusters()
            queryset = queryset.filter(cluster__in=clusters)
        return queryset


class UserAssetListView(generics.ListAPIView):
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetSerializer
    permission_classes = (IsValidUser,)

    def get_queryset(self):
        assets_granted = get_user_granted_assets(self.request.user)
        queryset = self.queryset.filter(
            id__in=[asset.id for asset in assets_granted]
        )
        return queryset


class AssetGroupViewSet(IDInFilterMixin, BulkModelViewSet):
    """
    Asset group api set, for add,delete,update,list,retrieve resource
    """
    queryset = AssetGroup.objects.all()
    serializer_class = serializers.AssetGroupSerializer
    permission_classes = (IsSuperUser,)


class GroupUpdateAssetsApi(generics.RetrieveUpdateAPIView):
    """
    Asset group, update it's asset member
    """
    queryset = AssetGroup.objects.all()
    serializer_class = serializers.GroupUpdateAssetsSerializer
    permission_classes = (IsSuperUser,)


class GroupAddAssetsApi(generics.UpdateAPIView):
    queryset = AssetGroup.objects.all()
    serializer_class = serializers.GroupUpdateAssetsSerializer
    permission_classes = (IsSuperUser,)

    def update(self, request, *args, **kwargs):
        group = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            assets = serializer.validated_data['assets']
            group.assets.add(*tuple(assets))
            return Response({"msg": "ok"})
        else:
            return Response({'error': serializer.errors}, status=400)


class ClusterViewSet(IDInFilterMixin, BulkModelViewSet):
    """
    Cluster api set, for add,delete,update,list,retrieve resource
    """
    queryset = Cluster.objects.all()
    serializer_class = serializers.ClusterSerializer
    permission_classes = (IsSuperUser,)


class ClusterTestAssetsAliveApi(generics.RetrieveAPIView):
    """
    Test cluster asset can connect using admin user or not
    """
    queryset = Cluster.objects.all()
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        cluster = self.get_object()
        admin_user = cluster.admin_user
        test_admin_user_connectability_manual.delay(admin_user)
        return Response("Task has been send, seen left assets status")


class ClusterAddAssetsApi(generics.UpdateAPIView):
    queryset = Cluster.objects.all()
    serializer_class = serializers.ClusterUpdateAssetsSerializer
    permission_classes = (IsSuperUser,)

    def update(self, request, *args, **kwargs):
        cluster = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            assets = serializer.validated_data['assets']
            for asset in assets:
                asset.cluster = cluster
                asset.save()
            return Response({"msg": "ok"})
        else:
            return Response({'error': serializer.errors}, status=400)


class AdminUserViewSet(IDInFilterMixin, BulkModelViewSet):
    """
    Admin user api set, for add,delete,update,list,retrieve resource
    """
    queryset = AdminUser.objects.all()
    serializer_class = serializers.AdminUserSerializer
    permission_classes = (IsSuperUser,)


class AdminUserAddClustersApi(generics.UpdateAPIView):
    queryset = AdminUser.objects.all()
    serializer_class = serializers.AdminUserUpdateClusterSerializer
    permission_classes = (IsSuperUser,)

    def update(self, request, *args, **kwargs):
        admin_user = self.get_object()
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            clusters = serializer.validated_data['clusters']
            for cluster in clusters:
                cluster.admin_user = admin_user
                cluster.save()
            return Response({"msg": "ok"})
        else:
            return Response({'error': serializer.errors}, status=400)


class SystemUserViewSet(BulkModelViewSet):
    """
    System user api set, for add,delete,update,list,retrieve resource
    """
    queryset = SystemUser.objects.all()
    serializer_class = serializers.SystemUserSerializer
    permission_classes = (IsSuperUserOrAppUser,)


class AssetListUpdateApi(IDInFilterMixin, ListBulkCreateUpdateDestroyAPIView):
    """
    Asset bulk update api
    """
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetSerializer
    permission_classes = (IsSuperUser,)


class SystemUserAuthInfoApi(generics.RetrieveAPIView):
    """
    Get system user auth info
    """
    queryset = SystemUser.objects.all()
    permission_classes = (IsSuperUserOrAppUser,)

    def retrieve(self, request, *args, **kwargs):
        system_user = self.get_object()
        data = {
            'id': system_user.id,
            'name': system_user.name,
            'username': system_user.username,
            'password': system_user.password,
            'private_key': system_user.private_key,
        }
        return Response(data)


class AssetRefreshHardwareApi(generics.RetrieveAPIView):
    """
    Refresh asset hardware info
    """
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetSerializer
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        asset_id = kwargs.get('pk')
        asset = get_object_or_404(Asset, pk=asset_id)
        summary = update_asset_hardware_info_manual(asset)[1]
        logger.debug("Refresh summary: {}".format(summary))
        if summary.get('dark'):
            return Response(summary['dark'].values(), status=501)
        else:
            return Response({"msg": "ok"})


class AssetAdminUserTestApi(generics.RetrieveAPIView):
    """
    Test asset admin user connectivity
    """
    queryset = Asset.objects.all()
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        asset_id = kwargs.get('pk')
        asset = get_object_or_404(Asset, pk=asset_id)
        ok, msg = test_asset_connectability_manual(asset)
        if ok:
            return Response({"msg": "pong"})
        else:
            return Response({"error": msg}, status=502)


class AdminUserTestConnectiveApi(generics.RetrieveAPIView):
    """
    Test asset admin user connectivity
    """
    queryset = AdminUser.objects.all()
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        admin_user = self.get_object()
        test_admin_user_connectability_manual.delay(admin_user)
        return Response({"msg": "Task created"})


class SystemUserPushApi(generics.RetrieveAPIView):
    """
    Push system user to cluster assets api
    """
    queryset = SystemUser.objects.all()
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        system_user = self.get_object()
        push_system_user_to_cluster_assets_manual.delay(system_user)
        return Response({"msg": "Task created"})


class SystemUserTestConnectiveApi(generics.RetrieveAPIView):
    """
    Push system user to cluster assets api
    """
    queryset = SystemUser.objects.all()
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        system_user = self.get_object()
        test_system_user_connectability_manual.delay(system_user)
        return Response({"msg": "Task created"})
