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
from .hands import IsSuperUser, IsValidUser, IsSuperUserOrAppUser, \
    get_user_granted_assets
from .models import AssetGroup, Asset, Cluster, SystemUser, AdminUser
from . import serializers
from .tasks import update_assets_hardware_info, test_admin_user_connectability, \
    test_admin_user_connectability_manual, push_system_user_to_cluster_assets, \
    test_system_user_connectability


class AssetViewSet(IDInFilterMixin, BulkModelViewSet):
    """
    API endpoint that allows Asset to be viewed or edited.
    """
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetSerializer
    permission_classes = (IsValidUser,)

    def get_queryset(self):
        if self.request.user.is_superuser or self.request.user.is_app:
            queryset = super().get_queryset()
        else:
            assets_granted = get_user_granted_assets(self.request.user)
            queryset = self.queryset.filter(id__in=[asset.id for asset in assets_granted])

        cluster_id = self.request.query_params.get('cluster_id')
        asset_group_id = self.request.query_params.get('asset_group_id')
        admin_user_id = self.request.query_params.get('admin_user_id')

        if cluster_id:
            queryset = queryset.filter(cluster__id=cluster_id)
        if asset_group_id:
            queryset = queryset.filter(groups__id=asset_group_id)
        if admin_user_id:
            admin_user = get_object_or_404(AdminUser, id=admin_user_id)
            assets_direct = [asset.id for asset in admin_user.asset_set.all()]
            clusters = [cluster.id for cluster in admin_user.cluster_set.all()]
            queryset = queryset.filter(Q(cluster__id__in=clusters)|Q(id__in=assets_direct))
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


class ClusterUpdateAssetsApi(generics.RetrieveUpdateAPIView):
    """
    Cluster update asset member
    """
    queryset = Cluster.objects.all()
    serializer_class = serializers.ClusterUpdateAssetsSerializer
    permission_classes = (IsSuperUser,)


class ClusterViewSet(IDInFilterMixin, BulkModelViewSet):
    """
    Cluster api set, for add,delete,update,list,retrieve resource
    """
    queryset = Cluster.objects.all()
    serializer_class = serializers.ClusterSerializer
    permission_classes = (IsSuperUser,)


# TOdo
class ClusterTestAssetsAliveApi(generics.RetrieveAPIView):
    """
    Test cluster asset can connect using admin user or not
    """
    queryset = Cluster.objects.all()
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        cluster = self.get_object()


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

    def update(self, request, *args, **kwargs):
        print(request.data)
        return super().update(request, *args, **kwargs)


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
        summary = update_assets_hardware_info([asset])
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
        ok, msg = test_admin_user_connectability_manual(asset)
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
        test_admin_user_connectability.delay(admin_user, force=True)
        return Response({"msg": "Task created"})


class SystemUserPushApi(generics.RetrieveAPIView):
    """
    Push system user to cluster assets api
    """
    queryset = SystemUser.objects.all()
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        system_user = self.get_object()
        push_system_user_to_cluster_assets.delay(system_user, force=True)
        return Response({"msg": "Task created"})


class SystemUserTestConnectiveApi(generics.RetrieveAPIView):
    """
    Push system user to cluster assets api
    """
    queryset = SystemUser.objects.all()
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        system_user = self.get_object()
        test_system_user_connectability.delay(system_user, force=True)
        return Response({"msg": "Task created"})
