# -*- coding: utf-8 -*-
#
from rest_framework.filters import SearchFilter as SearchFilterBase
import base64
import json
import logging
from functools import reduce
from operator import and_, or_
from collections import defaultdict
from django.utils import timezone

from django.core.cache import cache
from django.core.exceptions import (
    FieldDoesNotExist, ImproperlyConfigured,
    ValidationError as DjangoValidationError,
)
from django.db import models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as drf_filters
from rest_framework import filters
from rest_framework.compat import coreapi, coreschema
from rest_framework.fields import DateTimeField
from rest_framework.serializers import ValidationError
from rest_framework.filters import OrderingFilter

from common import const
from common.db.fields import RelatedManager

logger = logging.getLogger("jumpserver.common")

__all__ = [
    "LookupFilterBackend",
    "DatetimeRangeFilterBackend",
    "IDSpmFilterBackend",
    "IDInFilterBackend",
    "CustomFilterBackend",
    "BaseFilterSet",
    "IDNotFilterBackend",
    "LabelFilterBackend",
    "RewriteOrderingFilter",
    "AttrRulesFilterBackend",
]


class LookupFilterBackend(drf_filters.DjangoFilterBackend):
    """
    Preserve django-filter's default behavior while allowing explicit
    text, exact and ``__in`` lookups without per-view wiring.
    """
    dynamic_text_lookups = {
        "icontains", "startswith", "icontains_any", "icontains_all"
    }
    dynamic_multi_text_lookups = {"icontains_any", "icontains_all"}
    dynamic_value_lookups = {"exact", "in"}
    negated_text_lookups = {"icontains", "startswith"}
    negated_value_lookups = {"exact", "in"}

    def filter_queryset(self, request, queryset, view):
        queryset = super().filter_queryset(request, queryset, view)
        queryset = self.filter_primary_key(request, queryset)
        queryset = self.filter_dynamic_text_lookups(request, queryset, view)
        queryset = self.filter_dynamic_value_lookups(request, queryset, view)
        return self.filter_dynamic_negated_lookups(request, queryset, view)

    @staticmethod
    def filter_primary_key(request, queryset):
        value = request.query_params.get("id")
        if value in (None, "") or not hasattr(queryset, "model"):
            return queryset
        try:
            value = queryset.model._meta.pk.to_python(value)
        except (DjangoValidationError, TypeError, ValueError):
            return queryset.none()
        return queryset.filter(pk=value)

    def filter_dynamic_text_lookups(self, request, queryset, view):
        """Handle explicit text lookups like ``name__icontains=foo`` from filterset fields."""
        model = getattr(queryset, "model", None)
        if model is None:
            return queryset

        for param, values in request.query_params.lists():
            if "__" not in param:
                continue

            field_name, lookup = param.rsplit("__", 1)
            if lookup not in self.dynamic_text_lookups:
                continue
            if not self.is_allowed_filterset_field(view, field_name):
                continue
            if not self.is_allowed_filter_operator(
                view, field_name, lookup, "string"
            ):
                continue
            model_field_name = self.get_filterset_model_field(view, field_name)
            if not self.is_text_lookup_field(model, model_field_name):
                continue

            if lookup in self.dynamic_multi_text_lookups:
                orm_lookup = f"{model_field_name}__icontains"
                for raw_value in values:
                    cleaned_values = self.split_csv_values([raw_value])
                    if not cleaned_values:
                        continue
                    conditions = [
                        Q(**{orm_lookup: value}) for value in cleaned_values
                    ]
                    if lookup == "icontains_any":
                        queryset = queryset.filter(
                            reduce(or_, conditions)
                        )
                    else:
                        for condition in conditions:
                            queryset = queryset.filter(condition)
                if "__" in model_field_name:
                    queryset = queryset.distinct()
                continue

            for value in values:
                if value == "":
                    continue
                queryset = queryset.filter(
                    **{f"{model_field_name}__{lookup}": value}
                )
            if "__" in model_field_name:
                queryset = queryset.distinct()
        return queryset

    def is_text_lookup_field(self, model, field_path):
        field = self.resolve_model_field(model, field_path)
        return isinstance(field, (models.CharField, models.TextField))

    def filter_dynamic_value_lookups(self, request, queryset, view):
        """Handle explicit value lookups like ``name__exact=x`` and ``id__in=1,2``."""
        model = getattr(queryset, "model", None)
        if model is None:
            return queryset

        for param, values in request.query_params.lists():
            if "__" not in param:
                continue

            field_name, lookup = param.rsplit("__", 1)
            if lookup not in self.dynamic_value_lookups:
                continue
            if not self.is_allowed_filterset_field(view, field_name):
                continue
            if not self.is_allowed_filter_operator(
                view, field_name, lookup, "choice"
            ):
                continue
            model_field_name = self.get_filterset_model_field(view, field_name)
            if not self.is_value_lookup_field(model, model_field_name):
                continue

            if lookup == "exact":
                for value in values:
                    if value == "":
                        continue
                    queryset = self.apply_dynamic_value_lookup(
                        queryset, view, field_name,
                        **{model_field_name: value}
                    )
                if "__" in model_field_name:
                    queryset = queryset.distinct()
                continue

            for raw_value in values:
                cleaned_values = self.split_csv_values([raw_value])
                if not cleaned_values:
                    continue
                queryset = self.apply_dynamic_value_lookup(
                    queryset, view, field_name,
                    **{f"{model_field_name}__{lookup}": cleaned_values}
                )
                if "__" in model_field_name:
                    queryset = queryset.distinct()
        return queryset

    @staticmethod
    def apply_dynamic_value_lookup(
        queryset, view, field_name, negate=False, **kwargs
    ):
        filterset_class = getattr(view, "filterset_class", None)
        filter_field = (
            filterset_class.get_filters().get(field_name)
            if filterset_class
            else None
        )
        should_exclude = bool(
            getattr(filter_field, "exclude", False)
        ) ^ negate
        if should_exclude:
            return queryset.exclude(**kwargs)
        return queryset.filter(**kwargs)

    def is_value_lookup_field(self, model, field_path):
        field = self.resolve_model_field(model, field_path)
        if field is None:
            return False
        return not getattr(field, "is_relation", False)

    def filter_dynamic_negated_lookups(self, request, queryset, view):
        """Handle negated lookups such as ``name__icontains!=foo`` or ``id__in!=1,2``."""
        model = getattr(queryset, "model", None)
        if model is None:
            return queryset

        for raw_param, values in request.query_params.lists():
            if not raw_param.endswith("!"):
                continue

            param = raw_param[:-1]
            field_name, lookup = self.split_lookup_param(param)
            if lookup in self.negated_text_lookups:
                if not self.is_allowed_filterset_field(view, field_name):
                    continue
                if not self.is_allowed_filter_operator(
                    view, field_name, lookup, "string"
                ):
                    continue
                model_field_name = self.get_filterset_model_field(
                    view, field_name
                )
                if not self.is_text_lookup_field(model, model_field_name):
                    continue
                for value in values:
                    if value == "":
                        continue
                    queryset = queryset.exclude(
                        **{f"{model_field_name}__{lookup}": value}
                    )
                continue

            if lookup in self.negated_value_lookups:
                if not self.is_allowed_filterset_field(view, field_name):
                    continue
                if not self.is_allowed_filter_operator(
                    view, field_name, lookup, "choice"
                ):
                    continue
                model_field_name = self.get_filterset_model_field(
                    view, field_name
                )
                if not self.is_value_lookup_field(model, model_field_name):
                    continue
                if lookup == "in":
                    cleaned_values = self.split_csv_values(values)
                    if cleaned_values:
                        queryset = self.apply_dynamic_value_lookup(
                            queryset, view, field_name, negate=True,
                            **{
                                f"{model_field_name}__{lookup}":
                                cleaned_values
                            }
                        )
                else:
                    for value in values:
                        if value == "":
                            continue
                        queryset = self.apply_dynamic_value_lookup(
                            queryset, view, field_name, negate=True,
                            **{model_field_name: value}
                        )
        return queryset

    @staticmethod
    def split_lookup_param(param):
        if "__" not in param:
            return param, "exact"
        return tuple(param.rsplit("__", 1))

    @staticmethod
    def split_csv_values(values):
        cleaned_values = []
        for value in values:
            if value == "":
                continue
            cleaned_values.extend(
                item.strip() for item in value.split(",") if item.strip()
            )
        return cleaned_values

    def resolve_model_field(self, model, field_path):
        current_model = model
        field = None
        field_names = field_path.split("__")

        for index, field_name in enumerate(field_names):
            try:
                field = current_model._meta.get_field(field_name)
            except FieldDoesNotExist:
                return None

            if index == len(field_names) - 1:
                return field

            if not getattr(field, "is_relation", False) or not field.related_model:
                return None
            current_model = field.related_model

        return field

    def get_allowed_filterset_fields(self, view):
        filterset_fields = getattr(view, "filterset_fields", None) or ()
        if isinstance(filterset_fields, dict):
            fields = filterset_fields.keys()
        else:
            fields = filterset_fields

        filterset_class = getattr(view, "filterset_class", None)
        if filterset_class:
            fields = set(fields) | set(filterset_class.get_filters())

        fields = set(fields) | {"id"}

        return {
            self.normalize_search_field(field)
            for field in fields
            if self.normalize_search_field(field)
        }

    def is_allowed_filterset_field(self, view, query_key):
        field_name = self.get_lookup_field_name(query_key)
        return field_name in self.get_allowed_filterset_fields(view)

    @staticmethod
    def is_allowed_filter_operator(
        view, field_name, lookup, field_type
    ):
        from common.drf.metadata import SimpleMetadataWithFilters

        operators = SimpleMetadataWithFilters.get_field_filter_operators(
            view, field_name, {"type": field_type}
        )
        return lookup in operators

    @staticmethod
    def get_filterset_model_field(view, field_name):
        filterset_class = getattr(view, "filterset_class", None)
        if not filterset_class:
            return field_name
        filter_field = filterset_class.get_filters().get(field_name)
        if not filter_field:
            return field_name
        return filter_field.field_name or field_name

    def get_lookup_field_name(self, query_key):
        """Return the model field path without a supported lookup suffix."""
        query_key = self.normalize_search_field(query_key)
        if not query_key:
            return None
        query_key = query_key.rstrip("!")
        field_name, lookup = self.split_lookup_param(query_key)
        supported_lookups = (
            self.dynamic_text_lookups |
            self.dynamic_value_lookups |
            self.negated_text_lookups |
            self.negated_value_lookups
        )
        if lookup in supported_lookups:
            return field_name
        return query_key

    @staticmethod
    def normalize_search_field(field_name):
        if not field_name:
            return None
        if field_name[0] in ("^", "=", "@", "$"):
            field_name = field_name[1:]
        return field_name

class SearchFilter(SearchFilterBase):
    search_any_param = 'search__icontains_any'
    search_all_param = 'search__icontains_all'

    @staticmethod
    def split_search_groups(params):
        groups = []
        for group in params.replace('\x00', '').split(','):
            terms = [term for term in group.split() if term]
            if terms:
                groups.append(terms)
        return groups

    def get_search_terms(self, request):
        params, match_all = self.get_search_params(request)
        params = params.replace('\x00', '')  # strip null characters
        if match_all:
            params = params.replace(',', ' ')
        return params.split()

    def get_search_params(self, request):
        params, match_all = self.get_search_param_groups(request)
        return (params[-1] if params else ''), match_all

    def get_search_param_groups(self, request):
        if self.search_all_param in request.query_params:
            return request.query_params.getlist(self.search_all_param), True
        if self.search_any_param in request.query_params:
            return request.query_params.getlist(self.search_any_param), False
        params = request.query_params.getlist(self.search_param)
        if not params and self.search_param != 'search':
            params = request.query_params.getlist('search')
        return params, False

    def get_search_condition_groups(self, request):
        groups = []
        groups.extend(
            (params, True, False)
            for params in request.query_params.getlist(self.search_all_param)
        )
        groups.extend(
            (params, False, False)
            for params in request.query_params.getlist(self.search_any_param)
        )
        default_params = request.query_params.getlist(self.search_param)
        if not default_params and self.search_param != 'search':
            default_params = request.query_params.getlist('search')
        groups.extend((params, False, True) for params in default_params)
        return groups

    def must_call_distinct(self, queryset, search_fields):
        filtered_relations = getattr(
            getattr(queryset, 'query', None), '_filtered_relations', {}
        )
        if not filtered_relations:
            return super().must_call_distinct(queryset, search_fields)

        resolved_fields = []
        for search_field in search_fields:
            prefix = search_field[0] if search_field[0] in self.lookup_prefixes else ''
            field_name = search_field[len(prefix):]
            relation_alias, separator, related_field = field_name.partition('__')
            filtered_relation = filtered_relations.get(relation_alias)
            if filtered_relation:
                field_name = filtered_relation.relation_name
                if separator:
                    field_name = f'{field_name}__{related_field}'
            resolved_fields.append(f'{prefix}{field_name}')

        return super().must_call_distinct(queryset, resolved_fields)

    @staticmethod
    def split_default_search_batches(params):
        batches = []
        for raw_batch in params.replace('\x00', '').split(','):
            alternatives = []
            for raw_alternative in raw_batch.split('|'):
                terms = [
                    term for term in raw_alternative.split() if term
                ]
                if terms:
                    alternatives.append(terms)
            if alternatives:
                batches.append(alternatives)
        return batches

    def filter_queryset(self, request, queryset, view):
        search_fields = self.get_search_fields(view, request)
        search_condition_groups = self.get_search_condition_groups(request)

        if not search_fields or not search_condition_groups:
            return queryset

        orm_lookups = [
            self.construct_search(str(search_field), queryset)
            for search_field in search_fields
        ]

        for (
            raw_params, match_all, is_default_search
        ) in search_condition_groups:
            if is_default_search:
                search_batches = self.split_default_search_batches(raw_params)
                for alternatives in search_batches:
                    alternative_conditions = []
                    for terms in alternatives:
                        term_conditions = []
                        for term in terms:
                            queries = [
                                Q(**{orm_lookup: term})
                                for orm_lookup in orm_lookups
                            ]
                            term_conditions.append(reduce(or_, queries))
                        alternative_conditions.append(
                            reduce(and_, term_conditions)
                        )
                    queryset = queryset.filter(
                        reduce(or_, alternative_conditions)
                    )
                continue

            if match_all:
                raw_params = raw_params.replace(',', ' ')
            search_groups = self.split_search_groups(raw_params)
            if not search_groups:
                continue

            group_conditions = []
            for terms in search_groups:
                term_conditions = []
                for term in terms:
                    queries = [
                        Q(**{orm_lookup: term})
                        for orm_lookup in orm_lookups
                    ]
                    term_conditions.append(reduce(or_, queries))
                group_conditions.append(reduce(and_, term_conditions))

            queryset = queryset.filter(reduce(or_, group_conditions))

        if self.must_call_distinct(queryset, search_fields):
            queryset = queryset.filter(pk=models.OuterRef('pk'))
            queryset = view.get_queryset().filter(models.Exists(queryset))

        return queryset


class BaseFilterSet(drf_filters.FilterSet):
    days = drf_filters.NumberFilter(
        method="filter_days", label=_("Created days")
    )
    days__lt = drf_filters.NumberFilter(
        method="filter_days", label=_("Created days less than")
    )

    @classmethod
    def filter_for_field(cls, field, field_name, lookup_expr=None):
        """Use case-insensitive equality for generated plain-text filters."""
        meta_fields = cls._meta.fields
        explicitly_configured = (
            isinstance(meta_fields, dict)
            and lookup_expr in meta_fields.get(field_name, ())
        )
        is_plain_text_field = type(field) in (
            models.CharField,
            models.TextField,
        )
        if (
            lookup_expr == "exact"
            and is_plain_text_field
            and not field.choices
            and not explicitly_configured
        ):
            lookup_expr = "iexact"
        return super().filter_for_field(
            field, field_name, lookup_expr
        )

    def do_nothing(self, queryset, name, value):
        return queryset

    def get_query_param(self, k, default=None):
        if k in self.form.data:
            return self.form.cleaned_data[k]
        return default

    @staticmethod
    def filter_days(queryset, name, value):
        try:
            value = int(value)
        except ValueError:
            return queryset.none()

        if name == 'days':
            arg = 'date_created__gte'
        else:
            arg = 'date_created__lt'

        date = timezone.now() - timezone.timedelta(days=value)
        kwargs = {arg: date}
        return queryset.filter(**kwargs)


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
                        name=v,
                        location="query",
                        required=False,
                        type="string",
                        schema=coreschema.String(
                            title=v, description="%s %s" % (attr, v)
                        ),
                    )
                )

        return ret

    def _get_date_range_filter_fields(self, view):
        if not hasattr(view, "date_range_filter_fields"):
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
            """.format(
                view.name
            )
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
        fields = [
            coreapi.Field(
                name="spm",
                location="query",
                required=False,
                type="string",
                example="",
                description="Pre post objects id get spm id, then using filter",
            )
        ]
        fields.append(
            coreapi.Field(
                name="exclude_spm",
                location="query",
                required=False,
                type="string",
                example="",
                description="Pre post objects id get spm id, then using exclude",
            )
        )
        return fields

    @staticmethod
    def get_resource_ids(spm):
        cache_key = const.KEY_CACHE_RESOURCE_IDS.format(spm)
        resource_ids = cache.get(cache_key)
        if resource_ids is not None:
            cache.touch(cache_key, const.RESOURCE_IDS_CACHE_TIMEOUT)
        if isinstance(resource_ids, str):
            resource_ids = [resource_ids]
        return resource_ids

    def filter_queryset(self, request, queryset, view):
        spm = request.query_params.get("spm")
        if spm:
            resource_ids = self.get_resource_ids(spm)
            if resource_ids is None:
                return queryset.none()
            if hasattr(view, "filter_spm_queryset"):
                queryset = view.filter_spm_queryset(resource_ids, queryset)
            else:
                queryset = queryset.filter(id__in=resource_ids)

        exclude_spm = request.query_params.get("exclude_spm")
        if exclude_spm:
            resource_ids = self.get_resource_ids(exclude_spm)
            if resource_ids is None:
                return queryset
            if hasattr(view, "exclude_spm_queryset"):
                queryset = view.exclude_spm_queryset(resource_ids, queryset)
            else:
                queryset = queryset.exclude(id__in=resource_ids)
        return queryset


class IDInFilterBackend(filters.BaseFilterBackend):
    """
    Deprecated compatibility backend.

    Prefer the generic ``id__in=1,2,3`` syntax provided by LookupFilterBackend.
    """
    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name="ids",
                location="query",
                required=False,
                type="string",
                example="/api/v1/users/users?ids=1,2,3",
                description="Deprecated: filter by id set, prefer id__in",
            )
        ]

    def filter_queryset(self, request, queryset, view):
        ids = request.query_params.get("ids")
        if not ids:
            return queryset
        logger.warning(
            'Deprecated filter param "ids" used on %s, prefer "id__in"',
            request.path,
        )
        id_list = [i.strip() for i in ids.split(",")]
        queryset = queryset.filter(id__in=id_list)
        return queryset


class IDNotFilterBackend(filters.BaseFilterBackend):
    """
    Deprecated compatibility backend.

    Prefer the generic ``id__in!=1,2,3`` syntax provided by LookupFilterBackend.
    """
    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name="id!",
                location="query",
                required=False,
                type="string",
                example="/api/v1/users/users?id!=1,2,3",
                description="Deprecated: exclude by id set, prefer id__in!",
            )
        ]

    def filter_queryset(self, request, queryset, view):
        ids = request.query_params.get("id!")
        if not ids:
            return queryset
        logger.warning(
            'Deprecated filter param "id!" used on %s, prefer "id__in!"',
            request.path,
        )
        id_list = [i.strip() for i in ids.split(",")]
        queryset = queryset.exclude(id__in=id_list)
        return queryset


class LabelFilterBackend(filters.BaseFilterBackend):
    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name="label",
                location="query",
                required=False,
                type="string",
                example="/api/v1/users/users?label=abc",
                description="Filter by label",
            )
        ]

    @classmethod
    def parse_labels(cls, labels_id):
        from labels.models import Label

        grouped = cls.parse_label_groups(labels_id)
        label_ids = {
            label_id
            for group_label_ids in grouped.values()
            for label_id in group_label_ids
        }
        return list(Label.objects.filter(id__in=label_ids))

    @staticmethod
    def parse_label_groups(labels_id):
        """
        Resolve requested labels and group their IDs by label name.

        Values in one group are OR'ed; resource matches from separate groups
        are intersected later.
        """
        from labels.models import Label
        from django.core.exceptions import ValidationError as DjangoValidationError

        named_values = defaultdict(set)
        raw_label_ids = set()
        for item in labels_id.split(","):
            item = item.strip()
            if not item:
                continue
            if ":" not in item:
                raw_label_ids.add(item)
                continue
            name, value = item.split(":", 1)
            named_values[name.strip()].add(value.strip())

        grouped = defaultdict(set)
        for name, values in named_values.items():
            labels = Label.objects.filter(name=name)
            if "*" not in values:
                labels = labels.filter(value__in=values)
            grouped[name].update(labels.values_list("id", flat=True))

        if raw_label_ids:
            label_ids = set()
            has_invalid_id = False
            for label_id in raw_label_ids:
                try:
                    label_ids.add(Label._meta.pk.to_python(label_id))
                except (DjangoValidationError, TypeError, ValueError):
                    has_invalid_id = True

            labels = Label.objects.filter(id__in=label_ids)
            found_ids = set()
            for label in labels:
                found_ids.add(label.id)
                grouped[label.name].add(label.id)
            if has_invalid_id or found_ids != label_ids:
                grouped[None] = set()

        return grouped

    def filter_queryset(self, request, queryset, view):
        labels_id = request.query_params.get("labels")
        if not labels_id:
            return queryset

        if not hasattr(queryset, "model"):
            return queryset

        if not hasattr(queryset.model, "label_model"):
            return queryset

        model = queryset.model.label_model()
        labeled_resource_cls = model.labels.field.related_model
        app_label = model._meta.app_label
        model_name = model._meta.model_name

        full_resources = labeled_resource_cls.objects.filter(
            res_type__app_label=app_label,
            res_type__model=model_name,
        )
        grouped = self.parse_label_groups(labels_id)
        if not grouped or any(not label_ids for label_ids in grouped.values()):
            return queryset.none()

        matched_ids = None
        for label_ids in grouped.values():
            resources = model.filter_resources_by_labels(
                full_resources, label_ids, rel="any"
            )
            res_ids = resources.values_list("res_id", flat=True)
            if matched_ids is None:
                matched_ids = set(res_ids)
            else:
                matched_ids &= set(res_ids)
            if not matched_ids:
                return queryset.none()
        queryset = queryset.filter(id__in=matched_ids)
        return queryset


class CustomFilterBackend(filters.BaseFilterBackend):

    def get_schema_fields(self, view):
        fields = []
        defaults = dict(
            location="query", required=False, type="string", example="", description=""
        )
        if not hasattr(view, "custom_filter_fields"):
            return []

        for field in view.custom_filter_fields:
            if isinstance(field, str):
                defaults["name"] = field
            elif isinstance(field, dict):
                defaults.update(field)
            else:
                continue
            fields.append(coreapi.Field(**defaults))
        return fields

    def filter_queryset(self, request, queryset, view):
        return queryset


def current_user_filter(user_field="user"):
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
                name="attr_rules",
                location="query",
                required=False,
                type="string",
                example="/api/v1/users/users?attr_rules=jsonbase64",
                description='Filter by json like {"type": "attrs", "attrs": []} to base64',
            ),
            coreapi.Field(
                name="attr_rules_instance",
                location="query",
                required=False,
                type="string",
                example="/api/v1/users/users?attr_rules_instance=jsonbase64",
                description='Filter by json like {"app": "acls", "model": "LoginAssetACL", "id": "uuid"} to base64',
            )
        ]

    def filter_queryset(self, request, queryset, view):
        attr_rules = request.query_params.get("attr_rules")
        if attr_rules:
            attr_rules = self.json_base64_to_dict(attr_rules)
            return self.filter_queryset_by_attr_rules(attr_rules, queryset)
        
        attr_rules_instance = request.query_params.get("attr_rules_instance")
        if attr_rules_instance:
            attr_rules_instance = self.json_base64_to_dict(attr_rules_instance)
            return self.filter_queryset_by_attr_rules_instance(attr_rules_instance, queryset)

        return queryset

    def filter_queryset_by_attr_rules(self, attr_rules, queryset):
        qs = RelatedManager.get_to_filter_qs(attr_rules, queryset.model)
        for q in qs:
            queryset = queryset.filter(q)
        return queryset.distinct()
    
    def filter_queryset_by_attr_rules_instance(self, attr_rules_instance, queryset):
        if not attr_rules_instance or not isinstance(attr_rules_instance, dict):
            return queryset
        try:
            from django.apps import apps
            to_model = queryset.model
            instance_app = attr_rules_instance.get("app")
            instance_model = attr_rules_instance.get("model")
            instance_id = attr_rules_instance.get("id")
            instance_model_class = apps.get_model(instance_app, instance_model)
            instance = instance_model_class.objects.get(id=instance_id)
            field_name = f"{to_model.__name__.lower()}s"  # eg: assets, users
            queryset = getattr(instance, field_name).all()  # eg: login_asset_acl.users.all()
            return queryset
        except Exception as e:
            error = f"AttrRulesFilterBackend get_queryset_by_attr_rules_instance error: {e}"
            logger.error(error)
            raise ValidationError({'attr_rules_instance': error})
        
    def json_base64_to_dict(self, json_base64):
        try:
            json_data = base64.b64decode(json_base64.encode("utf-8"))
        except Exception:
            raise ValidationError({"attr_rules": "attr_rules should be base64"})
        try:
            data = json.loads(json_data)
        except Exception:
            raise ValidationError({"attr_rules": "attr_rules should be json"})

        logger.debug("AttrRulesFilterBackend json_base64 data: %s", data)
        return data

class RewriteOrderingFilter(OrderingFilter):
    default_ordering_if_has = ("name",)

    def get_default_ordering(self, view):
        ordering = super().get_default_ordering(view)
        # 如果 view.ordering = [] 表示不排序, 这样可以节约性能 (比如: 用户授权的资产)
        if ordering is not None:
            return ordering
        ordering_fields = getattr(view, "ordering_fields", self.ordering_fields)
        if ordering_fields:
            ordering = tuple(
                [f for f in ordering_fields if f in self.default_ordering_if_has]
            )
        return ordering
