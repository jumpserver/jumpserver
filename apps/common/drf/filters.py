# -*- coding: utf-8 -*-
#
from rest_framework import filters
from rest_framework.fields import DateTimeField
from rest_framework.serializers import ValidationError
from rest_framework.compat import coreapi, coreschema
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django_filters import rest_framework as drf_filters
import logging

from common import const

__all__ = [
    "DatetimeRangeFilter", "IDSpmFilter", 'IDInFilter', "CustomFilter",
    "BaseFilterSet"
]


class BaseFilterSet(drf_filters.FilterSet):
    def do_nothing(self, queryset, name, value):
        return queryset

    def get_query_param(self, k, default=None):
        if k in self.form.data:
            return self.form.cleaned_data[k]
        return default


class DatetimeRangeFilter(filters.BaseFilterBackend):
    def get_schema_fields(self, view):
        ret = []
        fields = self._get_date_range_filter_fields(view)

        for attr, date_range_keyword in fields.items():
            if len(date_range_keyword) != 2:
                continue
            for v in date_range_keyword:
                ret.append(
                    coreapi.Field(
                        name=v, location='query', required=False, type='string',
                        schema=coreschema.String(
                            title=v,
                            description='%s %s' % (attr, v)
                        )
                    )
                )

        return ret

    def _get_date_range_filter_fields(self, view):
        if not hasattr(view, 'date_range_filter_fields'):
            return {}
        try:
            return dict(view.date_range_filter_fields)
        except ValueError:
            msg = """
                View {} `date_range_filter_fields` set is improperly.
                For example:
                ```
                    class ExampleView:
                        date_range_filter_fields = [
                            ('db column', ('query param date from', 'query param date to'))
                        ]
                ```
            """.format(view.name)
            logging.error(msg)
            raise ImproperlyConfigured(msg)

    def filter_queryset(self, request, queryset, view):
        fields = self._get_date_range_filter_fields(view)

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
        if resources_id is None or not isinstance(resources_id, list):
            return queryset
        queryset = queryset.filter(id__in=resources_id)
        return queryset


class IDInFilter(filters.BaseFilterBackend):
    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name='ids', location='query', required=False,
                type='string', example='/api/v1/users/users?ids=1,2,3',
                description='Filter by id set'
            )
        ]

    def filter_queryset(self, request, queryset, view):
        ids = request.query_params.get('ids')
        if not ids:
            return queryset
        id_list = [i.strip() for i in ids.split(',')]
        queryset = queryset.filter(id__in=id_list)
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


def current_user_filter(user_field='user'):
    class CurrentUserFilter(filters.BaseFilterBackend):
        def filter_queryset(self, request, queryset, view):
            return queryset.filter(**{user_field: request.user})
    return CurrentUserFilter
