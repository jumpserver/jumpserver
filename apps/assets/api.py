# ~*~ coding: utf-8 ~*~

from rest_framework import viewsets, generics, mixins
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_bulk import BulkListSerializer, BulkSerializerMixin, ListBulkCreateUpdateDestroyAPIView
from django.shortcuts import get_object_or_404

from common.mixins import BulkDeleteApiMixin
from common.utils import get_object_or_none, signer
from .hands import IsSuperUserOrTerminalUser, IsSuperUser
from .models import AssetGroup, Asset, IDC, SystemUser, AdminUser
from . import serializers


class AssetGroupViewSet(viewsets.ModelViewSet):
    """ API endpoint that allows AssetGroup to be viewed or edited.
        some other comment
    """
    queryset = AssetGroup.objects.all()
    serializer_class = serializers.AssetGroupSerializer


class AssetViewSet(viewsets.ModelViewSet):
    """API endpoint that allows Asset to be viewed or edited."""
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetSerializer

    def get_queryset(self):
        queryset = super(AssetViewSet, self).get_queryset()
        idc = self.request.query_params.get('idc', '')
        if idc:
            queryset = queryset.filter(idc__id=idc)
        return queryset


class IDCViewSet(viewsets.ModelViewSet):
    """API endpoint that allows IDC to be viewed or edited."""
    queryset = IDC.objects.all()
    serializer_class = serializers.IDCSerializer
    permission_classes = (IsSuperUser,)


class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = AdminUser.objects.all()
    serializer_class = serializers.AdminUserSerializer
    permission_classes = (IsSuperUser,)


class SystemUserViewSet(viewsets.ModelViewSet):
    queryset = SystemUser.objects.all()
    serializer_class = serializers.SystemUserSerializer
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


class AssetListUpdateApi(BulkDeleteApiMixin, ListBulkCreateUpdateDestroyAPIView):
    queryset = Asset.objects.all()
    serializer_class = serializers.AssetBulkUpdateSerializer
    permission_classes = (IsSuperUser,)


class SystemUserAuthApi(APIView):
    permission_classes = (IsSuperUserOrTerminalUser,)

    def get(self, request, *args, **kwargs):
        system_user_id = request.query_params.get('system_user_id', -1)
        system_user_username = request.query_params.get('system_user_username', '')

        system_user = get_object_or_none(SystemUser, id=system_user_id, username=system_user_username)

        if system_user:
            if system_user.password:
                password = signer.sign(system_user.password)
            else:
                password = signer.sign('')

            if system_user.private_key:
                private_key = signer.sign(system_user.private_key)
            else:
                private_key = signer.sign(None)

            response = {
                'id': system_user.id,
                'password': password,
                'private_key': private_key,
            }

            return Response(response)
        else:
            return Response({'msg': 'error system user id or username'}, status=401)


