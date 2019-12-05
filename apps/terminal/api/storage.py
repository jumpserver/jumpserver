# coding: utf-8
#

from rest_framework import viewsets, generics, status
from rest_framework.response import Response
from django.utils.translation import ugettext_lazy as _

from common.permissions import IsSuperUser
from ..models import CommandStorage, ReplayStorage
from ..serializers import CommandStorageSerializer, ReplayStorageSerializer


__all__ = [
    'CommandStorageViewSet', 'CommandStorageTestConnectiveApi',
    'ReplayStorageViewSet', 'ReplayStorageTestConnectiveApi'
]


class BaseStorageViewSetMixin:

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if not instance.can_delete():
            data = {'msg': _('Deleting the default storage is not allowed')}
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)


class CommandStorageViewSet(BaseStorageViewSetMixin, viewsets.ModelViewSet):
    filter_fields = ('name', 'type',)
    search_fields = filter_fields
    queryset = CommandStorage.objects.all()
    serializer_class = CommandStorageSerializer
    permission_classes = (IsSuperUser,)


class ReplayStorageViewSet(BaseStorageViewSetMixin, viewsets.ModelViewSet):
    filter_fields = ('name', 'type',)
    search_fields = filter_fields
    queryset = ReplayStorage.objects.all()
    serializer_class = ReplayStorageSerializer
    permission_classes = (IsSuperUser,)


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


class CommandStorageTestConnectiveApi(BaseStorageTestConnectiveMixin,
                                      generics.RetrieveAPIView):
    queryset = CommandStorage.objects.all()


class ReplayStorageTestConnectiveApi(BaseStorageTestConnectiveMixin,
                                     generics.RetrieveAPIView):
    queryset = ReplayStorage.objects.all()
