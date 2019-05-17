#  coding: utf-8
#


from rest_framework import viewsets
from rest_framework.pagination import LimitOffsetPagination

from common.permissions import IsOrgAdmin

from ..models import RemoteAppPermission
from ..serializers import RemoteAppPermissionSerializer


__all__ = [
    'RemoteAppPermissionViewSet',
]


class RemoteAppPermissionViewSet(viewsets.ModelViewSet):
    filter_fields = ['name']
    queryset = RemoteAppPermission.objects.all()
    serializer_class = RemoteAppPermissionSerializer
    pagination_class = LimitOffsetPagination
    permission_classes = (IsOrgAdmin,)
