# -*- coding: utf-8 -*-
#
import coreapi
from rest_framework import filters
from rest_framework.fields import DateTimeField
from rest_framework.serializers import ValidationError
from django.core.cache import cache
import logging

from common import const

__all__ = ["DatetimeRangeFilter", "IDSpmFilter", "CustomFilter"]


class DatetimeRangeFilter(filters.BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if not hasattr(view, 'date_range_filter_fields'):
            return queryset
        try:
            fields = dict(view.date_range_filter_fields)
        except ValueError:
            msg = "View {} datetime_filter_fields set is error".format(view.name)
            logging.error(msg)
            return queryset
        kwargs = {}
        for attr, date_range_keyword in fields.items():
            if len(date_range_keyword) != 2:
                continue
            for i, v in enumerate(date_range_keyword):
                value = request.query_params.get(v)
                if not value:
                    continue
                try:
                    field = DateTimeField()
                    value = field.to_internal_value(value)
                    if i == 0:
                        lookup = "__gte"
                    else:
                        lookup = "__lte"
                    kwargs[attr+lookup] = value
                except ValidationError as e:
                    print(e)
                    continue
        if kwargs:
            queryset = queryset.filter(**kwargs)
        return queryset


class IDSpmFilter(filters.BaseFilterBackend):
    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name='spm', location='query', required=False,
                type='string', example='',
                description='Pre post objects id get spm id, then using filter'
            )
        ]

    def filter_queryset(self, request, queryset, view):
        spm = request.query_params.get('spm')
        if not spm:
            return queryset
        cache_key = const.KEY_CACHE_RESOURCES_ID.format(spm)
        resources_id = cache.get(cache_key)
        if not resources_id or not isinstance(resources_id, list):
            return queryset
        queryset = queryset.filter(id__in=resources_id)
        return queryset


class CustomFilter(filters.BaseFilterBackend):

    def get_schema_fields(self, view):
        fields = []
        defaults = dict(
            location='query', required=False,
            type='string', example='',
            description=''
        )
        if not hasattr(view, 'custom_filter_fields'):
            return []

        for field in view.custom_filter_fields:
            if isinstance(field, str):
                defaults['name'] = field
            elif isinstance(field, dict):
                defaults.update(field)
            else:
                continue
            fields.append(coreapi.Field(**defaults))
        return fields

    def filter_queryset(self, request, queryset, view):
        return queryset
