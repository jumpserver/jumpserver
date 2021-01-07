

from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.response import Response
from orgs.mixins.api import OrgBulkModelViewSet
from orgs.mixins import generics

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


class AdminUserViewSet(OrgBulkModelViewSet):
    """
    Admin user api set, for add,delete,update,list,retrieve resource
    """
    model = AdminUser
    filterset_fields = ("name", "username")
    search_fields = filterset_fields
    serializer_class = serializers.AdminUserSerializer
    permission_classes = (IsOrgAdmin,)

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.annotate(assets_amount=Count('assets'))
        return queryset

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        has_related_asset = instance.assets.exists()
        if has_related_asset:
            data = {'msg': _('Deleted failed, There are related assets')}
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)


class AdminUserAuthApi(generics.UpdateAPIView):
    model = AdminUser
    serializer_class = serializers.AdminUserAuthSerializer
    permission_classes = (IsOrgAdmin,)


class ReplaceNodesAdminUserApi(generics.UpdateAPIView):
    model = AdminUser
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
    model = AdminUser
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.TaskIDSerializer

    def retrieve(self, request, *args, **kwargs):
        admin_user = self.get_object()
        task = test_admin_user_connectivity_manual.delay(admin_user)
        return Response({"task": task.id})


class AdminUserAssetsListView(generics.ListAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.AssetSimpleSerializer
    filterset_fields = ("hostname", "ip")
    search_fields = filterset_fields

    def get_object(self):
        pk = self.kwargs.get('pk')
        return get_object_or_404(AdminUser, pk=pk)

    def get_queryset(self):
        admin_user = self.get_object()
        return admin_user.get_related_assets()
