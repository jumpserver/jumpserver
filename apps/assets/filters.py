# -*- coding: utf-8 -*-
#
from django.db.models import Q
from django.utils.translation import gettext as _
from rest_framework import serializers
from rest_framework import filters
from rest_framework.compat import coreapi, coreschema

from assets.utils import get_node_from_request, is_query_node_all_assets


def parse_protocol_filters(value):
    """Parse protocol search values such as ``ssh``, ``ssh/22`` and ``22``."""
    protocol_filters = []
    invalid = []
    for item in value.split(','):
        item = item.strip(' /')
        if not item:
            continue

        if '/' in item:
            parts = item.split('/')
            if len(parts) != 2:
                invalid.append(item)
                continue
            protocol_name, port_value = (part.strip() for part in parts)
            if not protocol_name or not port_value.isdigit():
                invalid.append(item)
                continue
            port = int(port_value)
            if port > 65535:
                invalid.append(item)
                continue
            protocol_filters.append(Q(name__iexact=protocol_name, port=port))
        elif item.isdigit():
            port = int(item)
            if port > 65535:
                invalid.append(item)
                continue
            protocol_filters.append(Q(port=port))
        elif item.lstrip('-').isdigit():
            invalid.append(item)
        else:
            protocol_filters.append(Q(name__iexact=item))

    if invalid:
        message = _('Invalid protocol filter: {}').format(', '.join(invalid))
        raise serializers.ValidationError({'protocols': message})
    return protocol_filters


class AssetByNodeFilterBackend(filters.BaseFilterBackend):
    fields = ['node', 'all']

    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name=field, location='query', required=False,
                type='string', example='', description='', schema=None,
            )
            for field in self.fields
        ]

    def filter_node_related_all(self, queryset, node):
        return queryset.filter(
            Q(nodes__key__istartswith=f'{node.key}:') |
            Q(nodes__key=node.key)
        ).distinct()

    def filter_node_related_direct(self, queryset, node):
        return queryset.filter(nodes__key=node.key).distinct()

    def filter_queryset(self, request, queryset, view):
        node = get_node_from_request(request)
        if node is None:
            return queryset

        query_all = is_query_node_all_assets(request)
        if query_all:
            return self.filter_node_related_all(queryset, node)
        else:
            return self.filter_node_related_direct(queryset, node)


class NodeFilterBackend(filters.BaseFilterBackend):
    """
    需要与 `assets.api.mixin.NodeFilterMixin` 配合使用
    """
    fields = ['node', 'all']

    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name=field, location='query', required=False,
                type='string', example='', description='', schema=None,
            )
            for field in self.fields
        ]

    def filter_queryset(self, request, queryset, view):
        node = get_node_from_request(request)
        if node is None:
            return queryset

        query_all = is_query_node_all_assets(request)
        if query_all:
            return queryset.filter(
                Q(nodes__key__startswith=f'{node.key}:') |
                Q(nodes__key=node.key)
            ).distinct()
        else:
            return queryset.filter(nodes__key=node.key).distinct()


class IpInFilterBackend(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        ips = request.query_params.get('ips')
        if not ips:
            return queryset
        ip_list = [i.strip() for i in ips.split(',')]
        queryset = queryset.filter(address__in=ip_list)
        return queryset

    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name='ips', location='query', required=False, type='string',
                schema=coreschema.String(
                    title='ips',
                    description='address in filter'
                )
            )
        ]
