# -*- coding: utf-8 -*-
#
import base64
import json
import logging

from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q
from django_filters import rest_framework as drf_filters
from rest_framework import filters
from rest_framework.compat import coreapi, coreschema
from rest_framework.fields import DateTimeField
from rest_framework.serializers import ValidationError

from common import const
from common.db.fields import RelatedManager

logger = logging.getLogger('jumpserver.common')

__all__ = [
    "DatetimeRangeFilterBackend", "IDSpmFilterBackend",
    'IDInFilterBackend', "CustomFilterBackend",
    "BaseFilterSet", 'IDNotFilterBackend',
    'NotOrRelFilterBackend', 'LabelFilterBackend',
]


class BaseFilterSet(drf_filters.FilterSet):
    def do_nothing(self, queryset, name, value):
        return queryset

    def get_query_param(self, k, default=None):
        if k in self.form.data:
            return self.form.cleaned_data[k]
        return default


class DatetimeRangeFilterBackend(filters.BaseFilterBackend):
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
            logger.error(msg)
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
                    kwargs[attr + lookup] = value
                except ValidationError as e:
                    print(e)
                    continue
        if kwargs:
            queryset = queryset.filter(**kwargs)
        return queryset


class IDSpmFilterBackend(filters.BaseFilterBackend):
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
        cache_key = const.KEY_CACHE_RESOURCE_IDS.format(spm)
        resource_ids = cache.get(cache_key)

        if resource_ids is None:
            return queryset.none()
        if isinstance(resource_ids, str):
            resource_ids = [resource_ids]
        if hasattr(view, 'filter_spm_queryset'):
            queryset = view.filter_spm_queryset(resource_ids, queryset)
        else:
            queryset = queryset.filter(id__in=resource_ids)
        return queryset


class IDInFilterBackend(filters.BaseFilterBackend):
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


class IDNotFilterBackend(filters.BaseFilterBackend):
    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name='id!', location='query', required=False,
                type='string', example='/api/v1/users/users?id!=1,2,3',
                description='Exclude by id set'
            )
        ]

    def filter_queryset(self, request, queryset, view):
        ids = request.query_params.get('id!')
        if not ids:
            return queryset
        id_list = [i.strip() for i in ids.split(',')]
        queryset = queryset.exclude(id__in=id_list)
        return queryset


class LabelFilterBackend(filters.BaseFilterBackend):
    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name='label', location='query', required=False,
                type='string', example='/api/v1/users/users?label=abc',
                description='Filter by label'
            )
        ]

    @staticmethod
    def parse_label_ids(labels_id):
        from labels.models import Label
        label_ids = [i.strip() for i in labels_id.split(',')]
        cleaned = []

        args = []
        for label_id in label_ids:
            kwargs = {}
            if ':' in label_id:
                k, v = label_id.split(':', 1)
                kwargs['name'] = k.strip()
                if v != '*':
                    kwargs['value'] = v.strip()
                args.append(kwargs)
            else:
                cleaned.append(label_id)

        if len(args) != 0:
            q = Q()
            for kwarg in args:
                q |= Q(**kwarg)
            ids = Label.objects.filter(q).values_list('id', flat=True)
            cleaned.extend(list(ids))
        return cleaned

    def filter_queryset(self, request, queryset, view):
        labels_id = request.query_params.get('labels')
        if not labels_id:
            return queryset

        if not hasattr(queryset, 'model'):
            return queryset

        if not hasattr(queryset.model, 'label_model'):
            return queryset

        model = queryset.model.label_model()
        labeled_resource_cls = model.labels.field.related_model
        app_label = model._meta.app_label
        model_name = model._meta.model_name

        resources = labeled_resource_cls.objects.filter(
            res_type__app_label=app_label, res_type__model=model_name,
        )
        label_ids = self.parse_label_ids(labels_id)
        resources = model.filter_resources_by_labels(resources, label_ids)
        res_ids = resources.values_list('res_id', flat=True)
        queryset = queryset.filter(id__in=set(res_ids))
        return queryset


class CustomFilterBackend(filters.BaseFilterBackend):

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


class UUIDInFilter(drf_filters.BaseInFilter, drf_filters.UUIDFilter):
    pass


class NumberInFilter(drf_filters.BaseInFilter, drf_filters.NumberFilter):
    pass


class AttrRulesFilterBackend(filters.BaseFilterBackend):
    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name='attr_rules', location='query', required=False,
                type='string', example='/api/v1/users/users?attr_rules=jsonbase64',
                description='Filter by json like {"type": "attrs", "attrs": []} to base64'
            )
        ]

    def filter_queryset(self, request, queryset, view):
        attr_rules = request.query_params.get('attr_rules')
        if not attr_rules:
            return queryset

        try:
            attr_rules = base64.b64decode(attr_rules.encode('utf-8'))
        except Exception:
            raise ValidationError({'attr_rules': 'attr_rules should be base64'})
        try:
            attr_rules = json.loads(attr_rules)
        except Exception:
            raise ValidationError({'attr_rules': 'attr_rules should be json'})

        logger.debug('attr_rules: %s', attr_rules)
        qs = RelatedManager.get_to_filter_qs(attr_rules, queryset.model)
        for q in qs:
            queryset = queryset.filter(q)
        return queryset.distinct()


class NotOrRelFilterBackend(filters.BaseFilterBackend):
    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name='_rel', location='query', required=False,
                type='string', example='/api/v1/users/users?name=abc&username=def&_rel=union',
                description='Filter by rel, or not, default is and'
            )
        ]

    def filter_queryset(self, request, queryset, view):
        _rel = request.query_params.get('_rel')
        if not _rel or _rel not in ('or', 'not'):
            return queryset
        if _rel == 'not':
            queryset.query.where.negated = True
        elif _rel == 'or':
            queryset.query.where.connector = 'OR'
        queryset._result_cache = None
        return queryset
