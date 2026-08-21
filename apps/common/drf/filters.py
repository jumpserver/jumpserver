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
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured
from django.db import models
from django.db.models import Q, F
from django.db.models.functions import Cast
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
    "NotOrRelFilterBackend",
    "LabelFilterBackend",
    "RewriteOrderingFilter",
    "AttrRulesFilterBackend",
]


class LookupFilterBackend(drf_filters.DjangoFilterBackend):
    """
    Preserve django-filter's default behavior while allowing explicit
    text lookups like ``field__icontains=value`` without per-view wiring.
    """
    dynamic_text_lookups = {"icontains", "startswith"}
    dynamic_value_lookups = {"in"}
    negated_text_lookups = {"icontains", "startswith"}
    negated_value_lookups = {"exact", "in"}

    def filter_queryset(self, request, queryset, view):
        queryset = super().filter_queryset(request, queryset, view)
        queryset = self.filter_dynamic_text_lookups(request, queryset)
        queryset = self.filter_dynamic_value_lookups(request, queryset)
        return self.filter_dynamic_negated_lookups(request, queryset)

    def filter_dynamic_text_lookups(self, request, queryset):
        model = getattr(queryset, "model", None)
        if model is None:
            return queryset

        for param, values in request.query_params.lists():
            if "__" not in param:
                continue

            field_name, lookup = param.rsplit("__", 1)
            if lookup not in self.dynamic_text_lookups:
                continue
            is_text_field = self.is_text_lookup_field(model, field_name)
            is_uuid_field = self.is_uuid_lookup_field(model, field_name)
            if not is_text_field and not is_uuid_field:
                continue

            for value in values:
                if value == "":
                    continue
                if is_text_field:
                    queryset = queryset.filter(**{param: value})
                else:
                    alias = f"_lookup_{field_name.replace('__', '_')}_text"
                    queryset = queryset.annotate(
                        **{alias: Cast(F(field_name), output_field=models.CharField())}
                    ).filter(**{f"{alias}__{lookup}": value})
        return queryset

    def is_text_lookup_field(self, model, field_path):
        field = self.resolve_model_field(model, field_path)
        return isinstance(field, (models.CharField, models.TextField))

    def is_uuid_lookup_field(self, model, field_path):
        return isinstance(self.resolve_model_field(model, field_path), models.UUIDField)

    def filter_dynamic_value_lookups(self, request, queryset):
        model = getattr(queryset, "model", None)
        if model is None:
            return queryset

        for param, values in request.query_params.lists():
            if "__" not in param:
                continue

            field_name, lookup = param.rsplit("__", 1)
            if lookup not in self.dynamic_value_lookups:
                continue
            if not self.is_value_lookup_field(model, field_name):
                continue

            cleaned_values = []
            for value in values:
                if value == "":
                    continue
                cleaned_values.extend(
                    item.strip() for item in value.split(",") if item.strip()
                )

            if cleaned_values:
                queryset = queryset.filter(**{param: cleaned_values})
        return queryset

    def is_value_lookup_field(self, model, field_path):
        field = self.resolve_model_field(model, field_path)
        if field is None:
            return False
        return not getattr(field, "is_relation", False)

    def filter_dynamic_negated_lookups(self, request, queryset):
        model = getattr(queryset, "model", None)
        if model is None:
            return queryset

        for raw_param, values in request.query_params.lists():
            if not raw_param.endswith("!"):
                continue

            param = raw_param[:-1]
            field_name, lookup = self.split_lookup_param(param)
            if lookup in self.negated_text_lookups:
                if not self.is_text_lookup_field(model, field_name):
                    continue
                for value in values:
                    if value == "":
                        continue
                    queryset = queryset.exclude(**{param: value})
                continue

            if lookup in self.negated_value_lookups:
                if not self.is_value_lookup_field(model, field_name):
                    continue
                if lookup == "in":
                    cleaned_values = self.split_csv_values(values)
                    if cleaned_values:
                        queryset = queryset.exclude(**{param: cleaned_values})
                else:
                    for value in values:
                        if value == "":
                            continue
                        queryset = queryset.exclude(**{field_name: value})
        return queryset

    @staticmethod
    def split_lookup_param(param):
        if "__" not in param:
            return param, "exact"
        return param.rsplit("__", 1)

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


class SearchFilter(SearchFilterBase):
    @staticmethod
    def split_search_groups(params):
        groups = []
        for group in params.replace('\x00', '').split(','):
            terms = [term for term in group.split() if term]
            if terms:
                groups.append(terms)
        return groups

    def get_search_terms(self, request):
        params = request.query_params.get(self.search_param, '') or request.query_params.get('search', '')
        params = params.replace('\x00', '')  # strip null characters
        return params.split()

    def filter_queryset(self, request, queryset, view):
        search_fields = self.get_search_fields(view, request)
        raw_params = request.query_params.get(self.search_param, '') or request.query_params.get('search', '')
        search_groups = self.split_search_groups(raw_params)

        if not search_fields or not search_groups:
            return queryset

        orm_lookups = [
            self.construct_search(str(search_field), queryset)
            for search_field in search_fields
        ]

        group_conditions = []
        for terms in search_groups:
            term_conditions = []
            for term in terms:
                queries = [Q(**{orm_lookup: term}) for orm_lookup in orm_lookups]
                term_conditions.append(reduce(or_, queries))
            group_conditions.append(reduce(and_, term_conditions))

        queryset = queryset.filter(reduce(or_, group_conditions))

        if self.must_call_distinct(queryset, search_fields):
            queryset = queryset.filter(pk=models.OuterRef('pk'))
            queryset = view.get_queryset().filter(models.Exists(queryset))

        return queryset


class BaseFilterSet(drf_filters.FilterSet):
    days = drf_filters.NumberFilter(method="filter_days")
    days__lt = drf_filters.NumberFilter(method="filter_days")

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
        return [
            coreapi.Field(
                name="spm",
                location="query",
                required=False,
                type="string",
                example="",
                description="Pre post objects id get spm id, then using filter",
            )
        ]

    def filter_queryset(self, request, queryset, view):
        spm = request.query_params.get("spm")
        if not spm:
            return queryset
        cache_key = const.KEY_CACHE_RESOURCE_IDS.format(spm)
        resource_ids = cache.get(cache_key)

        if resource_ids is None:
            return queryset.none()
        if isinstance(resource_ids, str):
            resource_ids = [resource_ids]
        if hasattr(view, "filter_spm_queryset"):
            queryset = view.filter_spm_queryset(resource_ids, queryset)
        else:
            queryset = queryset.filter(id__in=resource_ids)
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

    @staticmethod
    def parse_labels(labels_id):
        from labels.models import Label

        label_ids = [i.strip() for i in labels_id.split(",")]
        cleaned = []

        args = []
        for label_id in label_ids:
            kwargs = {}
            if ":" in label_id:
                k, v = label_id.split(":", 1)
                kwargs["name"] = k.strip()
                if v != "*":
                    kwargs["value"] = v.strip()
                args.append(kwargs)
            else:
                cleaned.append(label_id)

        if len(args) != 0:
            q = Q()
            for kwarg in args:
                q |= Q(**kwarg)
            labels = Label.objects.filter(q)
            cleaned.extend(list(labels))
        return cleaned

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
        labels = self.parse_labels(labels_id)
        grouped = defaultdict(set)
        for label in labels:
            grouped[label.name].add(label.id)

        matched_ids = set()
        for name, label_ids in grouped.items():
            resources = model.filter_resources_by_labels(
                full_resources, label_ids, rel="any"
            )
            res_ids = resources.values_list("res_id", flat=True)
            if not matched_ids:
                matched_ids = set(res_ids)
            else:
                matched_ids &= set(res_ids)
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

class NotOrRelFilterBackend(filters.BaseFilterBackend):
    def get_schema_fields(self, view):
        return [
            coreapi.Field(
                name="_rel",
                location="query",
                required=False,
                type="string",
                example="/api/v1/users/users?name=abc&username=def&_rel=union",
                description="Filter by rel, or not, default is and",
            )
        ]

    def filter_queryset(self, request, queryset, view):
        return queryset
        _rel = request.query_params.get("_rel")
        if not _rel or _rel not in ("or", "not"):
            return queryset
        if _rel == "not":
            queryset.query.where.negated = True
        elif _rel == "or":
            queryset.query.where.connector = "OR"
        queryset._result_cache = None
        return queryset


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
