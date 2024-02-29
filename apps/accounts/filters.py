# -*- coding: utf-8 -*-
#
from django.db.models import Q
from django_filters import rest_framework as drf_filters

from assets.models import Node
from common.drf.filters import BaseFilterSet
from .models import Account, GatheredAccount


class AccountFilterSet(BaseFilterSet):
    ip = drf_filters.CharFilter(field_name='address', lookup_expr='exact')
    hostname = drf_filters.CharFilter(field_name='name', lookup_expr='exact')
    username = drf_filters.CharFilter(field_name="username", lookup_expr='exact')
    address = drf_filters.CharFilter(field_name="asset__address", lookup_expr='exact')
    asset_id = drf_filters.CharFilter(field_name="asset", lookup_expr='exact')
    asset = drf_filters.CharFilter(field_name='asset', lookup_expr='exact')
    assets = drf_filters.CharFilter(field_name='asset_id', lookup_expr='exact')
    nodes = drf_filters.CharFilter(method='filter_nodes')
    node_id = drf_filters.CharFilter(method='filter_nodes')
    has_secret = drf_filters.BooleanFilter(method='filter_has_secret')
    platform = drf_filters.CharFilter(field_name='asset__platform_id', lookup_expr='exact')
    category = drf_filters.CharFilter(field_name='asset__platform__category', lookup_expr='exact')
    type = drf_filters.CharFilter(field_name='asset__platform__type', lookup_expr='exact')

    @staticmethod
    def filter_has_secret(queryset, name, has_secret):
        q = Q(secret__isnull=True) | Q(secret='')
        if has_secret:
            return queryset.exclude(q)
        else:
            return queryset.filter(q)

    @staticmethod
    def filter_nodes(queryset, name, value):
        nodes = Node.objects.filter(id=value)
        if not nodes:
            return queryset

        node_qs = Node.objects.none()
        for node in nodes:
            node_qs |= node.get_all_children(with_self=True)
        node_ids = list(node_qs.values_list('id', flat=True))
        queryset = queryset.filter(asset__nodes__in=node_ids)
        return queryset

    class Meta:
        model = Account
        fields = ['id', 'asset', 'source_id', 'secret_type']


class GatheredAccountFilterSet(BaseFilterSet):
    node_id = drf_filters.CharFilter(method='filter_nodes')
    asset_id = drf_filters.CharFilter(field_name='asset_id', lookup_expr='exact')
    asset_name = drf_filters.CharFilter(field_name='asset__name', lookup_expr='icontains')

    @staticmethod
    def filter_nodes(queryset, name, value):
        return AccountFilterSet.filter_nodes(queryset, name, value)

    class Meta:
        model = GatheredAccount
        fields = ['id', 'username']
