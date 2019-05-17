# coding: utf-8
#


from rest_framework.pagination import LimitOffsetPagination
from rest_framework_bulk import BulkModelViewSet

from ..hands import IsOrgAdmin
from ..models import RemoteApp
from ..serializers import RemoteAppSerializer


__all__ = [
    'RemoteAppViewSet',
]


class RemoteAppViewSet(BulkModelViewSet):
    filter_fields = ('name',)
    search_fields = filter_fields
    permission_classes = (IsOrgAdmin,)
    queryset = RemoteApp.objects.all()
    serializer_class = RemoteAppSerializer
    pagination_class = LimitOffsetPagination
