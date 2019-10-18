# coding: utf-8
#

from orgs.mixins.api import OrgBulkModelViewSet
from orgs.mixins import generics
from ..hands import IsOrgAdmin, IsAppUser
from ..models import RemoteApp
from ..serializers import RemoteAppSerializer, RemoteAppConnectionInfoSerializer


__all__ = [
    'RemoteAppViewSet', 'RemoteAppConnectionInfoApi',
]


class RemoteAppViewSet(OrgBulkModelViewSet):
    model = RemoteApp
    filter_fields = ('name',)
    search_fields = filter_fields
    permission_classes = (IsOrgAdmin,)
    serializer_class = RemoteAppSerializer


class RemoteAppConnectionInfoApi(generics.RetrieveAPIView):
    model = RemoteApp
    permission_classes = (IsAppUser, )
    serializer_class = RemoteAppConnectionInfoSerializer
