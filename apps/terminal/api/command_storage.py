# coding: utf-8
#

from rest_framework import viewsets

from common.permissions import IsSuperUser
from ..models import CommandStorage
from ..serializers import CommandStorageSerializer


__all__ = ['CommandStorageViewSet']


class CommandStorageViewSet(viewsets.ModelViewSet):
    filter_fields = ('name', 'type',)
    search_fields = filter_fields
    queryset = CommandStorage.objects.all()
    serializer_class = CommandStorageSerializer
    permission_classes = (IsSuperUser,)

