# ~*~ coding: utf-8 ~*~

from rest_framework import viewsets, generics, mixins


from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_bulk import BulkModelViewSet, BulkDestroyAPIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework_bulk import BulkListSerializer, BulkSerializerMixin, ListBulkCreateUpdateDestroyAPIView
from django.shortcuts import get_object_or_404

from common.mixins import IDInFilterMixin
from common.utils import get_object_or_none, signer
from .hands import IsSuperUser, IsAppUser, IsValidUser, get_user_granted_assets
from .models import AssetGroup, Asset, IDC, SystemUser, AdminUser
from . import serializers
from .tasks import update_assets_hardware_info


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
    queryset = AssetGroup.objects.all()
    serializer_class = serializers.AssetGroupSerializer
    permission_classes = (IsSuperUser,)


class AssetUpdateGroupApi(generics.RetrieveUpdateAPIView):
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetUpdateGroupSerializer
    permission_classes = (IsSuperUser,)


class AssetGroupUpdateApi(generics.RetrieveUpdateAPIView):
    queryset = AssetGroup.objects.all()
    serializer_class = serializers.AssetGroupUpdateSerializer
    permission_classes = (IsSuperUser,)


class AssetGroupUpdateSystemUserApi(generics.RetrieveUpdateAPIView):
    queryset = AssetGroup.objects.all()
    serializer_class = serializers.AssetGroupUpdateSystemUserSerializer
    permission_classes = (IsSuperUser,)


class IDCUpdateAssetsApi(generics.RetrieveUpdateAPIView):
    queryset = IDC.objects.all()
    serializer_class = serializers.IDCUpdateAssetsSerializer
    permission_classes = (IsSuperUser,)


class IDCViewSet(IDInFilterMixin, BulkModelViewSet):
    queryset = IDC.objects.all()
    serializer_class = serializers.IDCSerializer
    permission_classes = (IsSuperUser,)


class AdminUserViewSet(IDInFilterMixin, BulkModelViewSet):
    queryset = AdminUser.objects.all()
    serializer_class = serializers.AdminUserSerializer
    permission_classes = (IsSuperUser,)


class SystemUserViewSet(IDInFilterMixin, BulkModelViewSet):
    queryset = SystemUser.objects.all()
    serializer_class = serializers.SystemUserSerializer
    permission_classes = (IsSuperUser,)


class SystemUserUpdateApi(generics.RetrieveUpdateAPIView):
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetUpdateSystemUserSerializer
    permission_classes = (IsSuperUser,)


class SystemUserUpdateAssetsApi(generics.RetrieveUpdateAPIView):
    queryset = SystemUser.objects.all()
    serializer_class = serializers.SystemUserUpdateAssetsSerializer
    permission_classes = (IsSuperUser,)


class SystemUserUpdateAssetGroupApi(generics.RetrieveUpdateAPIView):
    queryset = SystemUser.objects.all()
    serializer_class = serializers.SystemUserUpdateAssetGroupSerializer
    permission_classes = (IsSuperUser,)


# class IDCAssetsApi(generics.ListAPIView):
#     model = IDC
#     serializer_class = serializers.AssetSerializer
#
#     def get(self, request, *args, **kwargs):
#         filter_kwargs = {self.lookup_field: self.kwargs[self.lookup_field]}
#         self.object = get_object_or_404(self.model, **filter_kwargs)
#         return super(IDCAssetsApi, self).get(request, *args, **kwargs)
#
#     def get_queryset(self):
#         return self.object.assets.all()


class AssetListUpdateApi(IDInFilterMixin, ListBulkCreateUpdateDestroyAPIView):
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetSerializer
    permission_classes = (IsSuperUser,)


class SystemUserAuthInfoApi(generics.RetrieveAPIView):
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
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetSerializer
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        asset_id = kwargs.get('pk')
        asset = get_object_or_404(Asset, pk=asset_id)
        update_assets_hardware_info([asset])
        return super(AssetRefreshHardwareView, self).retrieve(request, *args, **kwargs)
