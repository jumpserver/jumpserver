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
    serializer_class = RemoteAppSerializer

    def get_queryset(self):
        queryset = RemoteApp.objects.all()
        return queryset


class RemoteAppConnectionInfoApi(generics.RetrieveAPIView):
    permission_classes = (IsAppUser, )
    serializer_class = RemoteAppConnectionInfoSerializer

    def get_queryset(self):
        queryset = RemoteApp.objects.all()
        return queryset
