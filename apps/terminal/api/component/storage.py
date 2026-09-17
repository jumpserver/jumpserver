# coding: utf-8
#

from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as drf_filters
from django_filters import utils
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response

from common.api.mixin import CommonApiMixin
from common.const.http import GET, POST
from common.drf.filters import BaseFilterSet
from terminal import const
from terminal.filters import CommandStorageFilter, CommandFilter
from terminal.models import CommandStorage, ReplayStorage
from terminal.serializers import (
    CommandStorageSerializer, CommandStorageTreeMetricsSerializer,
    ReplayStorageSerializer,
)

__all__ = [
    'CommandStorageViewSet', 'CommandStorageTestConnectiveApi',
    'ReplayStorageViewSet', 'ReplayStorageTestConnectiveApi'
]


class BaseStorageViewSetMixin(CommonApiMixin):

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.type_null_or_server or instance.is_default:
            data = {'msg': _('Deleting the default storage is not allowed')}
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
        used_by = instance.used_by()
        if used_by:
            names = ', '.join(list(used_by.values_list('name', flat=True)))
            data = {'msg': _('Cannot delete storage that is being used: {}').format(names)}
            return Response(data=data, status=status.HTTP_400_BAD_REQUEST)
        return super().destroy(request, *args, **kwargs)


class CommandStorageViewSet(BaseStorageViewSetMixin, viewsets.ModelViewSet):
    search_fields = ('name', 'type')
    queryset = CommandStorage.objects.all()
    serializer_class = CommandStorageSerializer
    filterset_class = CommandStorageFilter
    rbac_perms = {
        'tree': 'terminal.view_commandstorage | terminal.view_command',
        'tree_metrics': 'terminal.view_commandstorage | terminal.view_command',
    }

    @action(methods=[GET], detail=False)
    def tree(self, request: Request):
        storage_qs = self.get_queryset().exclude(name='null')
        valid_storages = []
        invalid_storages = []

        for storage in storage_qs:
            if not storage.is_valid():
                invalid_storages.append(storage)
                continue
            valid_storages.append(storage)

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
                'name': f'{storage.name}({storage.type})',
                'title': f'{storage.name}({storage.type})',
                'pId': 'root',
                'isParent': False,
                'open': False,
                'valid': True,
            }
            for storage in valid_storages
        ]
        nodes.extend([
            {
                'id': storage.id,
                'name': f'{storage.name}({storage.type}) *{invalid}',
                'title': f'{storage.name}({storage.type})',
                'pId': 'root',
                'isParent': False,
                'open': False,
                'valid': False,
            }
            for storage in invalid_storages
        ])
        nodes.append(root)
        return Response(data=nodes)

    @action(
        methods=[POST], detail=False, url_path='tree-metrics',
        serializer_class=CommandStorageTreeMetricsSerializer,
    )
    def tree_metrics(self, request: Request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        node_ids = serializer.validated_data['node_ids']
        storages = self.get_queryset().exclude(name='null').filter(id__in=node_ids)
        storage_by_id = {storage.id: storage for storage in storages}
        results = []

        for storage_id in node_ids:
            storage = storage_by_id.get(storage_id)
            if not storage or not storage.is_valid():
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
                count = command_qs.count(limit_to_max_result_window=False)
            else:
                count = command_qs.count()
            results.append({'id': str(storage.id), 'count': count})

        return Response({'results': results})


class ReplayStorageFilterSet(BaseFilterSet):
    type_not = drf_filters.CharFilter(
        field_name='type', exclude=True, label=_('Exclude type')
    )

    class Meta:
        model = ReplayStorage
        fields = ['name', 'type', 'is_default', 'type_not']


class ReplayStorageViewSet(BaseStorageViewSetMixin, viewsets.ModelViewSet):
    search_fields = ('name', 'type', 'is_default')
    queryset = ReplayStorage.objects.all()
    serializer_class = ReplayStorageSerializer
    filterset_class = ReplayStorageFilterSet


class BaseStorageTestConnectiveMixin:
    error_keywords_map = [
        ('authentication failed', _('Authentication failed')),
        ('connection refused', _('Connection refused')),
        ('timed out', _('Connection timeout')),
        ('name or service not known', _('Unable to resolve the address')),
        ('no route to host', _('Unable to connect to the host')),
    ]

    def get_test_failure_msg(self, error):
        raw = str(error)
        lower = raw.lower()
        for keyword, message in self.error_keywords_map:
            if keyword in lower:
                return _("Test failure: {}").format(message)
        return _("Test failure: {}").format(raw)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            is_valid = instance.is_valid()
        except Exception as e:
            is_valid = False
            msg = self.get_test_failure_msg(e)
        else:
            if is_valid:
                msg = _("Test successful")
            else:
                msg = _("Test failure: Please check configuration")
        data = {
            'is_valid': is_valid,
            'msg': msg
        }
        return Response(data)


class CommandStorageTestConnectiveApi(BaseStorageTestConnectiveMixin, generics.RetrieveAPIView):
    queryset = CommandStorage.objects.all()
    rbac_perms = {
        'retrieve': 'terminal.view_commandstorage'
    }


class ReplayStorageTestConnectiveApi(BaseStorageTestConnectiveMixin, generics.RetrieveAPIView):
    queryset = ReplayStorage.objects.all()
    rbac_perms = {
        'retrieve': 'terminal.view_replaystorage'
    }
