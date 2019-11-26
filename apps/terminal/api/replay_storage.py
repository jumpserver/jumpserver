# coding: utf-8
#

from rest_framework import viewsets

from common.permissions import IsSuperUser
from ..models import ReplayStorage
from ..serializers import ReplayStorageSerializer


__all__ = ['ReplayStorageViewSet']


class ReplayStorageViewSet(viewsets.ModelViewSet):
    filter_fields = ('name', 'type',)
    search_fields = filter_fields
    queryset = ReplayStorage.objects.all()
    serializer_class = ReplayStorageSerializer
    permission_classes = (IsSuperUser,)

