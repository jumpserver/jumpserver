# coding: utf-8
#

from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as drf_filters
from django_filters import utils
from rest_framework import viewsets, generics
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from common.api.mixin import CommonApiMixin
from common.const.http import GET
from common.drf.filters import BaseFilterSet
from common.storage.mixins import StorageDestroyModelMixin, StorageTestConnectiveMixin
from terminal import const
from terminal.filters import CommandStorageFilter, CommandFilter, CommandFilterForStorageTree
from terminal.models import CommandStorage, ReplayStorage
from terminal.serializers import CommandStorageSerializer, ReplayStorageSerializer

__all__ = [
    'CommandStorageViewSet', 'CommandStorageTestConnectiveApi',
    'ReplayStorageViewSet', 'ReplayStorageTestConnectiveApi'
]


class CommandStorageViewSet(
    StorageDestroyModelMixin, CommonApiMixin, viewsets.ModelViewSet
):
    search_fields = ('name', 'type')
    queryset = CommandStorage.objects.all()
    serializer_class = CommandStorageSerializer
    filterset_class = CommandStorageFilter
    rbac_perms = {
        'tree': 'terminal.view_commandstorage | terminal.view_command'
    }

    @action(methods=[GET], detail=False, filterset_class=CommandFilterForStorageTree)
    def tree(self, request: Request):
        storage_qs = self.get_queryset().exclude(name='null')
        storages_with_count = []
        invalid_storages = []

        for storage in storage_qs:
            if not storage.is_valid():
                invalid_storages.append(storage)
                continue

            command_qs = storage.get_command_queryset()
            filterset = CommandFilter(
                data=request.query_params, queryset=command_qs,
                request=request
            )
            if not filterset.is_valid():
                raise utils.translate_validation(filterset.errors)
            command_qs = filterset.qs
            if storage.type == const.CommandStorageType.es:
                command_count = command_qs.count(limit_to_max_result_window=False)
            else:
                command_count = command_qs.count()
            storages_with_count.append((storage, command_count))

        root = {
            'id': 'root',
            'name': _('Command storages'),
            'title': _('Command storages'),
            'pId': '',
            'isParent': True,
            'open': True,
        }

        invalid = _('Invalid')
        nodes = [
                    {
                        'id': storage.id,
                        'name': f'{storage.name}({storage.type}) ({command_count})',
                        'title': f'{storage.name}({storage.type})',
                        'pId': 'root',
                        'isParent': False,
                        'open': False,
                        'valid': True,
                    } for storage, command_count in storages_with_count
                ] + [
                    {
                        'id': storage.id,
                        'name': f'{storage.name}({storage.type}) *{invalid}',
                        'title': f'{storage.name}({storage.type})',
                        'pId': 'root',
                        'isParent': False,
                        'open': False,
                        'valid': False,
                    } for storage in invalid_storages
                ]
        nodes.append(root)
        return Response(data=nodes)


class ReplayStorageFilterSet(BaseFilterSet):
    type_not = drf_filters.CharFilter(field_name='type', exclude=True)

    class Meta:
        model = ReplayStorage
        fields = ['name', 'type', 'is_default', 'type_not']


class ReplayStorageViewSet(
    StorageDestroyModelMixin, CommonApiMixin, viewsets.ModelViewSet
):
    search_fields = ('name', 'type', 'is_default')
    queryset = ReplayStorage.objects.all()
    serializer_class = ReplayStorageSerializer
    filterset_class = ReplayStorageFilterSet


class CommandStorageTestConnectiveApi(StorageTestConnectiveMixin, generics.RetrieveAPIView):
    queryset = CommandStorage.objects.all()
    rbac_perms = {
        'retrieve': 'terminal.view_commandstorage'
    }


class ReplayStorageTestConnectiveApi(StorageTestConnectiveMixin, generics.RetrieveAPIView):
    queryset = ReplayStorage.objects.all()
    rbac_perms = {
        'retrieve': 'terminal.view_replaystorage'
    }
