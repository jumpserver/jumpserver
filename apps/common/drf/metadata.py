# -*- coding: utf-8 -*-
#
from __future__ import unicode_literals

import datetime
from collections import OrderedDict

from django.core.exceptions import (
    FieldDoesNotExist, ImproperlyConfigured, PermissionDenied,
)
from django.db import models
from django.http import Http404
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as drf_filters
from rest_framework import exceptions, serializers
from rest_framework.fields import empty
from rest_framework.metadata import SimpleMetadata
from rest_framework.request import clone_request

from common.serializers.fields import TreeChoicesField


class SimpleMetadataWithFilters(SimpleMetadata):
    """Override SimpleMetadata, adding info about filters"""

    text_filter_operators = (
        "icontains", "exact", "startswith",
        "icontains_any", "icontains_all", "in"
    )
    value_filter_operators = ("exact", "in")
    exact_filter_operators = ("exact",)
    search_filter_operators = ("icontains_any", "icontains_all")
    supported_filter_operators = set(text_filter_operators)
    search_param = "search"
    ordering_param = "order"

    methods = {"PUT", "POST", "GET", "PATCH"}
    attrs = [
        "read_only", "label", "help_text",
        "min_length", "max_length", "min_value",
        "max_value", "write_only",
    ]

    def determine_actions(self, request, view):
        """
        For generic class based views we return information about
        the fields that are accepted for 'PUT' and 'POST' methods.
        """
        actions = {}
        view.raw_action = getattr(view, "action", None)
        query_action = request.query_params.get("action", None)
        for method in self.methods & set(view.allowed_methods):
            if hasattr(view, "action_map"):
                view.action = view.action_map.get(method.lower(), view.action)

            if query_action and query_action.lower() != method.lower():
                continue

            view.request = clone_request(request, method)
            try:
                # Test global permissions
                if hasattr(view, "check_permissions"):
                    view.check_permissions(view.request)
                # Test object permissions
                if method == "PUT" and hasattr(view, "get_object"):
                    view.get_object()
            except (exceptions.APIException, PermissionDenied, Http404):
                pass
            else:
                # If user has appropriate permissions for the view, include
                # appropriate metadata about the fields that should be supplied.
                serializer = view.get_serializer()
                actions[method] = self.get_serializer_info(serializer)
            finally:
                view.request = request
        return actions

    def get_field_type(self, field):
        """
        Given a field, return a string representing the type of the field.
        """
        tp = self.label_lookup[field]

        class_name = field.__class__.__name__
        if class_name == "LabeledChoiceField":
            tp = "labeled_choice"
        elif class_name == "JSONField":
            tp = 'json'
        elif class_name == "ObjectRelatedField":
            tp = "object_related_field"
        elif class_name == "ManyRelatedField":
            child_relation_class_name = field.child_relation.__class__.__name__
            if child_relation_class_name == "ObjectRelatedField":
                tp = "m2m_related_field"
        return tp

    @staticmethod
    def set_choices_field(field, field_info):
        field_info["choices"] = [
            {
                "value": choice_value,
                "label": force_str(choice_label, strings_only=True),
            }
            for choice_value, choice_label in dict(field.choices).items()
        ]

    @staticmethod
    def set_tree_field(field, field_info):
        field_info["tree"] = field.tree
        field_info["type"] = "tree"

    @staticmethod
    def set_style_field(field, field_info):
        style = getattr(field, "style", None)
        if not style:
            return

        if isinstance(style, dict):
            if style.get("base_template") == "textarea.html":
                field_info["style"] = "textarea"
            elif style:
                field_info["style"] = style
            return

        field_info["style"] = force_str(style, strings_only=True)

    def get_field_info(self, field):
        """
        Given an instance of a serializer field, return a dictionary
        of metadata about it.
        """
        field_info = OrderedDict()
        field_info["type"] = self.get_field_type(field)
        field_info["required"] = getattr(field, "required", False)

        # Default value
        default = getattr(field, "default", None)
        if default is not None and default != empty:
            if isinstance(default, (str, int, bool, float, datetime.datetime, list)):
                field_info["default"] = default

        for attr in self.attrs:
            value = getattr(field, attr, None)
            if value is not None and value != "":
                field_info[attr] = force_str(value, strings_only=True)

        self.set_style_field(field, field_info)

        if getattr(field, "child", None):
            field_info["child"] = self.get_field_info(field.child)
        elif getattr(field, "fields", None):
            field_info["children"] = self.get_serializer_info(field)

        if isinstance(field, TreeChoicesField):
            self.set_tree_field(field, field_info)
        elif isinstance(field, serializers.ChoiceField):
            self.set_choices_field(field, field_info)

        if field.field_name == 'id':
            field_info['label'] = 'ID'
        if field.field_name == 'org_id':
            field_info['label'] = _('Org ID')

        return field_info

    @classmethod
    def get_filters_fields(cls, view):
        fields = []
        if getattr(view, "filterset_class", None):
            filterset_class = view.filterset_class
            meta = getattr(filterset_class, "Meta", None)
            meta_fields = getattr(meta, "fields", ()) or ()
            if isinstance(meta_fields, dict):
                meta_fields = meta_fields.keys()
            fields = list(meta_fields)
        elif hasattr(view, "filterset_fields"):
            fields = view.filterset_fields
        elif hasattr(view, "filter_fields"):
            fields = view.filter_fields

        if hasattr(view, "custom_filter_fields"):
            # 不能写 fields += view.custom_filter_fields
            # 会改变 view 的 filter_fields
            fields = list(fields) + list(view.custom_filter_fields)

        if isinstance(fields, dict):
            fields = list(fields.keys())

        model = cls.get_filterset_model(view)
        if model is not None and getattr(model._meta, "pk", None) is not None:
            fields = ["id", *fields]
        return list(dict.fromkeys(fields))

    @staticmethod
    def get_ordering_fields(view):
        return getattr(view, "ordering_fields", ())

    @staticmethod
    def get_search_fields(view):
        return getattr(view, "search_fields", ())

    @staticmethod
    def get_filterset_class(view):
        filterset_class = getattr(view, "filterset_class", None)
        if filterset_class is not None:
            return filterset_class
        if not getattr(view, "filterset_fields", None):
            return None

        queryset = getattr(view, "queryset", None)
        model = getattr(view, "model", None)
        if queryset is None and model is not None:
            queryset = model._default_manager.all()
        if queryset is None:
            try:
                queryset = view.get_queryset()
            except Exception:
                return None
        return drf_filters.DjangoFilterBackend().get_filterset_class(
            view, queryset
        )

    @classmethod
    def get_filterset_model(cls, view):
        filterset_class = cls.get_filterset_class(view)
        model = getattr(getattr(filterset_class, "Meta", None), "model", None)
        if model is not None:
            return model

        queryset = getattr(view, "queryset", None)
        if queryset is not None:
            return getattr(queryset, "model", None)
        model = getattr(view, "model", None)
        if model is not None:
            return model

        try:
            queryset = view.get_queryset()
        except Exception:
            return None
        return getattr(queryset, "model", None)

    @staticmethod
    def resolve_model_field(model, field_path):
        if model is None or not field_path:
            return None

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
            if not getattr(field, "is_relation", False):
                return None
            current_model = getattr(field, "related_model", None)
            if current_model is None:
                return None
        return field

    @staticmethod
    def get_filter_field_type(filter_field, model_field):
        if isinstance(
            filter_field,
            (drf_filters.ChoiceFilter, drf_filters.MultipleChoiceFilter),
        ):
            return "choice"
        if getattr(model_field, "choices", None):
            return "choice"
        if isinstance(filter_field, drf_filters.BooleanFilter):
            return "boolean"
        if isinstance(filter_field, drf_filters.UUIDFilter):
            return "uuid"
        if isinstance(filter_field, drf_filters.DateTimeFilter):
            return "datetime"
        if isinstance(filter_field, drf_filters.DateFilter):
            return "date"
        if isinstance(filter_field, drf_filters.NumberFilter):
            return "number"

        if isinstance(model_field, models.BooleanField):
            return "boolean"
        if isinstance(model_field, models.UUIDField):
            return "uuid"
        if isinstance(model_field, models.EmailField):
            return "email"
        if isinstance(model_field, (models.CharField, models.TextField)):
            return "string"
        if isinstance(model_field, models.DateTimeField):
            return "datetime"
        if isinstance(model_field, models.DateField):
            return "date"
        if isinstance(model_field, models.IntegerField):
            return "integer"
        if isinstance(
            model_field,
            (models.DecimalField, models.FloatField),
        ):
            return "number"

        return "string"

    @staticmethod
    def get_filter_choices(filter_field, model_field):
        choices = getattr(model_field, "choices", None)
        if not choices and filter_field is not None:
            choices = filter_field.extra.get("choices")
        if not choices:
            return []
        return [
            {
                "value": value,
                "label": force_str(label, strings_only=True),
            }
            for value, label in choices
            if value not in ("", None)
        ]

    @staticmethod
    def get_metadata_field_label(field_name, field_info, filter_field, model_field):
        label = getattr(filter_field, "_label", None)
        if label:
            return force_str(label, strings_only=True)
        label = field_info.get("label")
        if label:
            return label
        label = getattr(filter_field, "label", None)
        if label:
            return force_str(label, strings_only=True)
        model_field_name = (
            getattr(filter_field, "field_name", "") or field_name
        )
        verbose_name = getattr(model_field, "verbose_name", None)
        if verbose_name and "__" not in model_field_name:
            return force_str(verbose_name, strings_only=True)
        return field_name.replace("__", " ").replace("_", " ").capitalize()

    @classmethod
    def get_filters_metadata(cls, view, serializer_fields):
        filterset_class = cls.get_filterset_class(view)
        base_filters = (
            filterset_class.get_filters()
            if filterset_class is not None
            else {}
        )
        field_names = cls.get_filters_fields(view)
        filters_metadata = OrderedDict()
        if not field_names:
            return filters_metadata
        model = cls.get_filterset_model(view)

        for field_name in dict.fromkeys(field_names):
            filter_field = base_filters.get(field_name)
            model_field_name = (
                getattr(filter_field, "field_name", None) or field_name
            )
            model_field = cls.resolve_model_field(model, model_field_name)
            serializer_info = serializer_fields.get(field_name, {})
            field_type = cls.get_filter_field_type(filter_field, model_field)
            field_info = {
                "label": cls.get_metadata_field_label(
                    field_name, serializer_info, filter_field, model_field
                ),
                "type": field_type,
            }
            help_text = serializer_info.get("help_text")
            if help_text:
                field_info["help_text"] = help_text
            choices = (
                serializer_info.get("choices")
                or cls.get_filter_choices(filter_field, model_field)
            )
            if choices:
                field_info["type"] = "choice"
                field_info["choices"] = choices
            field_info["operators"] = cls.get_field_filter_operators(
                view, field_name, field_info
            )
            if filter_field is not None:
                field_info["lookup"] = filter_field.lookup_expr
                if filter_field.exclude:
                    field_info["exclude"] = True
                if getattr(filter_field, "method", None):
                    field_info["custom"] = True
            filters_metadata[field_name] = field_info
        return filters_metadata

    @classmethod
    def get_ordering_metadata(cls, view, serializer_fields):
        field_names = cls.get_ordering_fields(view)
        if field_names == "__all__":
            field_names = list(serializer_fields.keys())
        field_names = list(field_names or [])
        fields = []
        model = (
            cls.get_filterset_model(view)
            if field_names
            else None
        )
        for field_name in dict.fromkeys(field_names):
            normalized_name = field_name.lstrip("-")
            field_info = serializer_fields.get(normalized_name, {})
            model_field = cls.resolve_model_field(model, normalized_name)
            fields.append({
                "name": normalized_name,
                "label": cls.get_metadata_field_label(
                    normalized_name, field_info, None, model_field
                ),
            })

        default = getattr(view, "ordering", None)
        if isinstance(default, str):
            default = [default]
        elif default is None:
            default = ["name"] if "name" in field_names else []
        else:
            default = list(default)
        return {
            "param": cls.ordering_param,
            "fields": fields,
            "default": default,
        }

    @classmethod
    def get_search_metadata(cls, view, serializer_fields):
        lookup_prefixes = {
            "^": "startswith",
        }
        fields = []
        for raw_field_name in cls.get_search_fields(view):
            if not isinstance(raw_field_name, str) or not raw_field_name:
                continue
            prefix = raw_field_name[0] if raw_field_name else ""
            field_name = (
                raw_field_name[1:]
                if prefix in lookup_prefixes
                else raw_field_name
            )
            field_info = serializer_fields.get(field_name, {})
            fields.append({
                "name": field_name,
                "label": cls.get_metadata_field_label(
                    field_name, field_info, None, None
                ),
                "lookup": lookup_prefixes.get(prefix, "icontains"),
            })

        return {
            "param": cls.search_param,
            "fields": fields,
            "operators": (
                list(cls.search_filter_operators) if fields else []
            ),
            "default_operator": (
                "icontains_any" if fields else None
            ),
        }

    @classmethod
    def get_configured_filter_operators(cls, view, field_name):
        filterset_class = cls.get_filterset_class(view)
        meta = getattr(filterset_class, "Meta", None)
        fields_operator = getattr(meta, "fields_operator", {}) or {}
        if not isinstance(fields_operator, dict):
            raise ImproperlyConfigured(
                "FilterSet.Meta.fields_operator must be a dict"
            )
        if field_name not in fields_operator:
            return None

        operators = fields_operator[field_name]
        if not isinstance(operators, (list, tuple)):
            raise ImproperlyConfigured(
                "FilterSet.Meta.fields_operator values must be lists or tuples"
            )
        unsupported = set(operators) - cls.supported_filter_operators
        if unsupported:
            raise ImproperlyConfigured(
                "Unsupported filter operators: {}".format(
                    ", ".join(sorted(unsupported))
                )
            )
        return list(dict.fromkeys(operators))

    @classmethod
    def get_filterset_filter(cls, view, field_name):
        filterset_class = cls.get_filterset_class(view)
        if filterset_class is None:
            return None
        return getattr(filterset_class, "base_filters", {}).get(field_name)

    @classmethod
    def infer_filter_operators(cls, view, field_name, field_info):
        filter_field = cls.get_filterset_filter(view, field_name)
        field_type = field_info.get("type")
        if (
            isinstance(filter_field, drf_filters.BooleanFilter)
            or field_type == "boolean"
        ):
            return list(cls.exact_filter_operators)
        if getattr(filter_field, "method", None):
            return list(cls.exact_filter_operators)
        if field_type == "string" and (
            filter_field is None
            or isinstance(filter_field, drf_filters.CharFilter)
        ):
            return list(cls.text_filter_operators)
        return list(cls.value_filter_operators)

    @classmethod
    def get_field_filter_operators(cls, view, field_name, field_info):
        configured = cls.get_configured_filter_operators(view, field_name)
        if configured is not None:
            return configured
        return cls.infer_filter_operators(view, field_name, field_info)

    def determine_metadata(self, request, view):
        metadata = super(SimpleMetadataWithFilters, self).determine_metadata(
            request, view
        )
        meta_get = metadata.get("actions", {}).get("GET", {})
        metadata["filters"] = self.get_filters_metadata(
            view, meta_get
        )
        metadata["ordering"] = self.get_ordering_metadata(
            view, meta_get
        )
        metadata["search"] = self.get_search_metadata(
            view, meta_get
        )
        return metadata
