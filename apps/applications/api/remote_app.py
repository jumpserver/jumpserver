# coding: utf-8
#


from rest_framework import generics

from orgs.mixins.api import OrgBulkModelViewSet
from ..hands import IsOrgAdmin, IsAppUser
from ..models import RemoteApp
from ..serializers import RemoteAppSerializer, RemoteAppConnectionInfoSerializer


__all__ = [
    'RemoteAppViewSet', 'RemoteAppConnectionInfoApi',
]


class RemoteAppViewSet(OrgBulkModelViewSet):
    filter_fields = ('name',)
    search_fields = filter_fields
    permission_classes = (IsOrgAdmin,)
    queryset = RemoteApp.objects.all()
    serializer_class = RemoteAppSerializer


class RemoteAppConnectionInfoApi(generics.RetrieveAPIView):
    queryset = RemoteApp.objects.all()
    permission_classes = (IsAppUser, )
    serializer_class = RemoteAppConnectionInfoSerializer
