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

from common.mixins import IDInFilterMixin
from common.utils import get_object_or_none
from .hands import IsSuperUser, IsAppUser, IsValidUser, \
    get_user_granted_assets, push_users
from .models import AssetGroup, Asset, IDC, SystemUser, AdminUser
from . import serializers
from .tasks import update_assets_hardware_info
from .utils import test_admin_user_connective_manual


class AssetViewSet(IDInFilterMixin, BulkModelViewSet):
    """API endpoint that allows Asset to be viewed or edited."""
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetSerializer
    permission_classes = (IsValidUser,)

    def get_queryset(self):
        if self.request.user.is_superuser:
            queryset = super(AssetViewSet, self).get_queryset()
        else:
            queryset = get_user_granted_assets(self.request.user)
        idc_id = self.request.query_params.get('idc_id', '')
        system_users_id = self.request.query_params.get('system_user_id', '')
        asset_group_id = self.request.query_params.get('asset_group_id', '')
        admin_user_id = self.request.query_params.get('admin_user_id', '')
        if idc_id:
            queryset = queryset.filter(idc__id=idc_id)
        if system_users_id:
            queryset = queryset.filter(system_users__id=system_users_id)
        if admin_user_id:
            queryset = queryset.filter(admin_user__id=admin_user_id)
        if asset_group_id:
            queryset = queryset.filter(groups__id=asset_group_id)
        return queryset


class AssetGroupViewSet(IDInFilterMixin, BulkModelViewSet):
    """Asset group api set, for add,delete,update,list,retrieve resource"""
    queryset = AssetGroup.objects.all()
    serializer_class = serializers.AssetGroupSerializer
    permission_classes = (IsSuperUser,)


class AssetUpdateGroupApi(generics.RetrieveUpdateAPIView):
    """Asset update it's group api"""
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetUpdateGroupSerializer
    permission_classes = (IsSuperUser,)


class AssetGroupUpdateApi(generics.RetrieveUpdateAPIView):
    """Asset group, update it's asset member"""
    queryset = AssetGroup.objects.all()
    serializer_class = serializers.AssetGroupUpdateSerializer
    permission_classes = (IsSuperUser,)


class AssetGroupUpdateSystemUserApi(generics.RetrieveUpdateAPIView):
    """Asset group push system user"""
    queryset = AssetGroup.objects.all()
    serializer_class = serializers.AssetGroupUpdateSystemUserSerializer
    permission_classes = (IsSuperUser,)


class IDCUpdateAssetsApi(generics.RetrieveUpdateAPIView):
    """IDC update asset member"""
    queryset = IDC.objects.all()
    serializer_class = serializers.IDCUpdateAssetsSerializer
    permission_classes = (IsSuperUser,)


class IDCViewSet(IDInFilterMixin, BulkModelViewSet):
    """IDC api set, for add,delete,update,list,retrieve resource"""
    queryset = IDC.objects.all()
    serializer_class = serializers.IDCSerializer
    permission_classes = (IsSuperUser,)


class AdminUserViewSet(IDInFilterMixin, BulkModelViewSet):
    """Admin user api set, for add,delete,update,list,retrieve resource"""
    queryset = AdminUser.objects.all()
    serializer_class = serializers.AdminUserSerializer
    permission_classes = (IsSuperUser,)


class SystemUserViewSet(IDInFilterMixin, BulkModelViewSet):
    """System user api set, for add,delete,update,list,retrieve resource"""
    queryset = SystemUser.objects.all()
    serializer_class = serializers.SystemUserSerializer
    permission_classes = (IsSuperUser,)


class SystemUserUpdateApi(generics.RetrieveUpdateAPIView):
    """Asset update it's system user

    when update then push system user to asset.
    """
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetUpdateSystemUserSerializer
    permission_classes = (IsSuperUser,)

    def patch(self, request, *args, **kwargs):
        asset = self.get_object()
        old_system_users = set(asset.system_users.all())
        response = super(SystemUserUpdateApi, self).patch(request, *args, **kwargs)
        system_users_new = set(asset.system_users.all())
        system_users = system_users_new - old_system_users
        system_users = [system_user._to_secret_json() for system_user in system_users]
        push_users.delay([asset._to_secret_json()], system_users)
        return response


class SystemUserUpdateAssetsApi(generics.RetrieveUpdateAPIView):
    """System user update it's assets"""
    queryset = SystemUser.objects.all()
    serializer_class = serializers.SystemUserUpdateAssetsSerializer
    permission_classes = (IsSuperUser,)


class SystemUserUpdateAssetGroupApi(generics.RetrieveUpdateAPIView):
    """System user update asset group"""
    queryset = SystemUser.objects.all()
    serializer_class = serializers.SystemUserUpdateAssetGroupSerializer
    permission_classes = (IsSuperUser,)


class AssetListUpdateApi(IDInFilterMixin, ListBulkCreateUpdateDestroyAPIView):
    """Asset bulk update api"""
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetSerializer
    permission_classes = (IsSuperUser,)


class SystemUserAuthInfoApi(generics.RetrieveAPIView):
    """Get system user auth info"""
    queryset = SystemUser.objects.all()
    permission_classes = (IsAppUser,)

    def retrieve(self, request, *args, **kwargs):
        system_user = self.get_object()
        data = {
            'id': system_user.id,
            'name': system_user.name,
            'username': system_user.username,
            'password': system_user.password,
            'private_key': system_user.private_key,
            'auth_method': system_user.auth_method,
        }
        return Response(data)


class AssetRefreshHardwareView(generics.RetrieveAPIView):
    """Refresh asset hardware info"""
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetSerializer
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        asset_id = kwargs.get('pk')
        asset = get_object_or_404(Asset, pk=asset_id)
        summary = update_assets_hardware_info([asset])
        if len(summary['failed']) == 0:
            return super(AssetRefreshHardwareView, self).retrieve(request, *args, **kwargs)
        else:
            return Response('', status=502)


class AssetAdminUserTestView(AssetRefreshHardwareView):
    """Test asset admin user connectivity"""
    queryset = Asset.objects.all()
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        asset_id = kwargs.get('pk')
        asset = get_object_or_404(Asset, pk=asset_id)
        result = test_admin_user_connective_manual([asset])
        if result:
            return Response('1')
        else:
            return Response('0', status=502)


class AssetGroupPushSystemUserView(generics.UpdateAPIView):
    """Asset group push system user api"""
    queryset = AssetGroup.objects.all()
    permission_classes = (IsSuperUser,)
    serializer_class = serializers.AssetSerializer

    def patch(self, request, *args, **kwargs):
        asset_group = self.get_object()
        assets = asset_group.assets.all()
        system_user_id = self.request.data['system_user']
        system_user = get_object_or_none(SystemUser, id=system_user_id)
        if not assets or not system_user:
            return Response('Invalid system user id or asset group id', status=404)
        task = push_users.delay([asset._to_secret_json() for asset in assets],
                                system_user._to_secret_json())
        return Response(task.id)
