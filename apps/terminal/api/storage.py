# coding: utf-8
#

from rest_framework import viewsets, generics
from rest_framework.response import Response
from django.utils.translation import ugettext_lazy as _

from common.permissions import IsSuperUser
from ..models import CommandStorage, ReplayStorage
from ..serializers import CommandStorageSerializer, ReplayStorageSerializer


__all__ = [
    'CommandStorageViewSet', 'CommandStorageTestConnectiveApi',
    'ReplayStorageViewSet', 'ReplayStorageTestConnectiveApi'
]


class BaseStorageTestConnectiveMixin:
    permission_classes = (IsSuperUser,)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            is_valid = instance.is_valid()
        except Exception as e:
            is_valid = False
            msg = _("Test failure: {}".format(str(e)))
        else:
            if is_valid:
                msg = _("Test successful")
            else:
                msg = _("Test failure: Account invalid")
        data = {
            'is_valid': is_valid,
            'msg': msg
        }
        return Response(data)


class CommandStorageViewSet(viewsets.ModelViewSet):
    filter_fields = ('name', 'type',)
    search_fields = filter_fields
    queryset = CommandStorage.objects.all()
    serializer_class = CommandStorageSerializer
    permission_classes = (IsSuperUser,)


class CommandStorageTestConnectiveApi(BaseStorageTestConnectiveMixin,
                                      generics.RetrieveAPIView):
    queryset = CommandStorage.objects.all()


class ReplayStorageViewSet(viewsets.ModelViewSet):
    filter_fields = ('name', 'type',)
    search_fields = filter_fields
    queryset = ReplayStorage.objects.all()
    serializer_class = ReplayStorageSerializer
    permission_classes = (IsSuperUser,)


class ReplayStorageTestConnectiveApi(BaseStorageTestConnectiveMixin,
                                     generics.RetrieveAPIView):
    queryset = ReplayStorage.objects.all()
