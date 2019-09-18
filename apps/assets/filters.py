# -*- coding: utf-8 -*-
#

import coreapi
from rest_framework import filters
from django.db.models import Q

from common.utils import dict_get_any, is_uuid, get_object_or_none
from .models import Node, Label


class AssetByNodeFilterBackend(filters.BaseFilterBackend):
    fields = ['node', 'all']

    # def filter_node(self, queryset):
    #     node_id = self.request.query_params.get("node_id")
    #     if not node_id:
    #         return queryset
    #
    #     node = get_object_or_404(Node, id=node_id)
    #     show_current_asset = self.request.query_params.get("show_current_asset") in ('1', 'true')
    #
    #     # 当前节点是顶层节点, 并且仅显示直接资产
    #     if node.is_org_root() and show_current_asset:
    #         queryset = queryset.filter(
    #             Q(nodes=node_id) | Q(nodes__isnull=True)
    #         ).distinct()
    #     # 当前节点是顶层节点，显示所有资产
    #     elif node.is_org_root() and not show_current_asset:
    #         return queryset
    #     # 当前节点不是鼎城节点，只显示直接资产
    #     elif not node.is_org_root() and show_current_asset:
    #         queryset = queryset.filter(nodes=node)
    #     else:
    #         children = node.get_all_children(with_self=True)
    #         queryset = queryset.filter(nodes__in=children).distinct()
    #     return queryset

    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name=field, location='query', required=False,
                type='string', example='', description=''
            )
            for field in self.fields
        ]

    def filter_queryset(self, request, queryset, view):
        node_id = dict_get_any(request.query_params, ['node', 'node_id'])
        if not node_id:
            return queryset
        query_all_arg = request.query_params.get('all')
        show_current_asset_arg = request.query_params.get('show_current_asset')

        query_all = query_all_arg == '1'
        if show_current_asset_arg is not None:
            query_all = show_current_asset_arg != '1'

        if is_uuid(node_id):
            node = get_object_or_none(Node, id=node_id)
        else:
            node = get_object_or_none(Node, key=node_id)

        if not node:
            return queryset.none()

        if query_all:
            pattern = node.get_all_children_pattern(with_self=True)
        else:
            pattern = node.get_children_key_pattern(with_self=True)
        return queryset.filter(nodes__key__regex=pattern)


class LabelFilterBackend(filters.BaseFilterBackend):
    sep = '#'
    query_arg = 'label'

    def get_schema_fields(self, view):
        example = self.sep.join(['os', 'linux'])
        return [
            coreapi.Field(
                name=self.query_arg, location='query', required=False,
                type='string', example=example, description=''
            )
        ]

    def get_query_labels(self, request):
        labels_query = request.query_params.getlist(self.query_arg)
        if not labels_query:
            return None

        q = None
        for kv in labels_query:
            if self.sep not in kv:
                continue
            key, value = kv.strip().split(self.sep)[:2]
            if not all([key, value]):
                continue
            if q:
                q |= Q(name=key, value=value)
            else:
                q = Q(name=key, value=value)
        if not q:
            return []
        labels = Label.objects.filter(q, is_active=True)\
            .values_list('id', flat=True)
        return labels

    def filter_queryset(self, request, queryset, view):
        labels = self.get_query_labels(request)
        if labels is None:
            return queryset
        if len(labels) == 0:
            return queryset.none()
        for label in labels:
            queryset = queryset.filter(labels=label)
        return queryset


