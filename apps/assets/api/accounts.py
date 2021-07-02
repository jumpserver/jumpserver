from django.db.models import F
from django.conf import settings
from rest_framework.decorators import action
from rest_framework.response import Response

from orgs.mixins.api import OrgBulkModelViewSet
from common.permissions import IsOrgAdmin, IsOrgAdminOrAppUser, NeedMFAVerify
from ..models import AuthBook
from .. import serializers

__all__ = ['AccountViewSet']


class AccountViewSet(OrgBulkModelViewSet):
    model = AuthBook
    filterset_fields = ("username", "asset", "systemuser")
    search_fields = filterset_fields
    serializer_classes = {
        'default': serializers.AccountSerializer,
        'retrieve_auth_info': serializers.AccountAuthInfoSerializer
    }
    permission_classes = (IsOrgAdmin,)

    @action(methods=['GET'], detail=True, url_path='auth-info', permission_classes=[IsOrgAdmin, NeedMFAVerify])
    def retrieve_auth_info(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def get_queryset(self):
        queryset = super().get_queryset()\
            .annotate(ip=F('asset__ip'))\
            .annotate(hostname=F('asset__hostname'))
        return queryset

    def get_permissions(self):
        if self.action != 'retrieve_auth_info':
            return super().get_permissions()

        if not settings.SECURITY_VIEW_AUTH_NEED_MFA:
            self.permission_classes = [IsOrgAdminOrAppUser]
        return super().get_permissions()
