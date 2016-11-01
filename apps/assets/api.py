# ~*~ coding: utf-8 ~*~

from rest_framework import serializers
from rest_framework import viewsets, serializers, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_bulk import BulkListSerializer, BulkSerializerMixin, ListBulkCreateUpdateDestroyAPIView

from common.mixins import BulkDeleteApiMixin
from common.utils import get_object_or_none, signer
from .hands import IsSuperUserOrTerminalUser, IsSuperUser
from .models import AssetGroup, Asset, IDC, SystemUser
from .serializers import AssetBulkUpdateSerializer


class AssetGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetGroup


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        # fields = ('id', 'title', 'code', 'linenos', 'language', 'style')


class IDCSerializer(serializers.ModelSerializer):
    class Meta:
        model = IDC
        # fields = ('id', 'title', 'code', 'linenos', 'language', 'style')


class AssetGroupViewSet(viewsets.ModelViewSet):
    """ API endpoint that allows AssetGroup to be viewed or edited.

    some other comment

    """
    queryset = AssetGroup.objects.all()
    serializer_class = AssetGroupSerializer


class AssetViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows Asset to be viewed or edited.
    """
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer


class IDCViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows IDC to be viewed or edited.
    """
    queryset = IDC.objects.all()
    serializer_class = IDCSerializer
    permission_classes = (IsSuperUser,)


class AssetListUpdateApi(BulkDeleteApiMixin, ListBulkCreateUpdateDestroyAPIView):
    queryset = Asset.objects.all()
    serializer_class = AssetBulkUpdateSerializer
    permission_classes = (IsSuperUser,)


class SystemUserAuthApi(APIView):
    permission_classes = (IsSuperUserOrTerminalUser,)

    def get(self, request, *args, **kwargs):
        system_user_id = request.query_params.get('system_user_id', -1)
        system_user_username = request.query_params.get('system_user_username', '')

        system_user = get_object_or_none(SystemUser, id=system_user_id, username=system_user_username)

        if system_user:
            password = signer.sign(system_user.password)
            private_key = signer.sign(system_user.private_key)

            response = {
                'id': system_user.id,
                'password': password,
                'private_key': private_key,
            }

            return Response(response)
        else:
            return Response({'msg': 'error system user id or username'}, status=401)


