# -*- coding: utf-8 -*-
#
from __future__ import unicode_literals

import datetime
from collections import OrderedDict

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, serializers
from rest_framework.fields import empty
from rest_framework.metadata import SimpleMetadata
from rest_framework.request import clone_request

from common.serializers.fields import TreeChoicesField


class SimpleMetadataWithFilters(SimpleMetadata):
    """Override SimpleMetadata, adding info about filters"""

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
        for method in self.methods & set(view.allowed_methods):
            if hasattr(view, "action_map"):
                view.action = view.action_map.get(method.lower(), view.action)

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
            field_info['label'] = _('Organization ID')

        return field_info

    @staticmethod
    def get_filters_fields(request, view):
        fields = []
        if hasattr(view, "get_filter_fields"):
            fields = view.get_filter_fields(request)
        elif hasattr(view, "filter_fields"):
            fields = view.filter_fields
        elif hasattr(view, "filterset_fields"):
            fields = view.filterset_fields
        elif hasattr(view, "get_filterset_fields"):
            fields = view.get_filterset_fields(request)
        elif hasattr(view, "filterset_class"):
            fields = list(view.filterset_class.Meta.fields) + list(
                view.filterset_class.declared_filters.keys()
            )

        if hasattr(view, "custom_filter_fields"):
            # 不能写 fields += view.custom_filter_fields
            # 会改变 view 的 filter_fields
            fields = list(fields) + list(view.custom_filter_fields)

        if isinstance(fields, dict):
            fields = list(fields.keys())
        return fields

    @staticmethod
    def get_ordering_fields(request, view):
        fields = []
        if hasattr(view, "get_ordering_fields"):
            fields = view.get_ordering_fields(request)
        elif hasattr(view, "ordering_fields"):
            fields = view.ordering_fields
        return fields

    def determine_metadata(self, request, view):
        metadata = super(SimpleMetadataWithFilters, self).determine_metadata(
            request, view
        )
        filterset_fields = self.get_filters_fields(request, view)
        order_fields = self.get_ordering_fields(request, view)

        meta_get = metadata.get("actions", {}).get("GET", {})
        for k, v in meta_get.items():
            if k in filterset_fields:
                v["filter"] = True
            if k in order_fields:
                v["order"] = True
        return metadata
