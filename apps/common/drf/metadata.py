# -*- coding: utf-8 -*-
#
from __future__ import unicode_literals

from collections import OrderedDict

from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.utils.encoding import force_text

from rest_framework.metadata import SimpleMetadata
from rest_framework import exceptions, serializers
from rest_framework.request import clone_request


class SimpleMetadataWithFilters(SimpleMetadata):
    """Override SimpleMetadata, adding info about filters"""

    methods = {"PUT", "POST", "GET"}
    attrs = [
        'read_only', 'label', 'help_text',
        'min_length', 'max_length',
        'min_value', 'max_value', "write_only"
    ]

    def determine_actions(self, request, view):
        """
        For generic class based views we return information about
        the fields that are accepted for 'PUT' and 'POST' methods.
        """
        actions = {}
        for method in self.methods & set(view.allowed_methods):
            view.request = clone_request(request, method)
            try:
                # Test global permissions
                if hasattr(view, 'check_permissions'):
                    view.check_permissions(view.request)
                # Test object permissions
                if method == 'PUT' and hasattr(view, 'get_object'):
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

    def get_field_info(self, field):
        """
        Given an instance of a serializer field, return a dictionary
        of metadata about it.
        """
        field_info = OrderedDict()
        field_info['type'] = self.label_lookup[field]
        field_info['required'] = getattr(field, 'required', False)

        for attr in self.attrs:
            value = getattr(field, attr, None)
            if value is not None and value != '':
                field_info[attr] = force_text(value, strings_only=True)

        if getattr(field, 'child', None):
            field_info['child'] = self.get_field_info(field.child)
        elif getattr(field, 'fields', None):
            field_info['children'] = self.get_serializer_info(field)

        if (not field_info.get('read_only') and
            not isinstance(field, (serializers.RelatedField, serializers.ManyRelatedField)) and
                hasattr(field, 'choices')):
            field_info['choices'] = [
                {
                    'value': choice_value,
                    'display_name': force_text(choice_name, strings_only=True)
                }
                for choice_value, choice_name in field.choices.items()
            ]

        return field_info

    def get_filters_fields(self, request, view):
        fields = []
        if hasattr(view, 'get_filter_fields'):
            fields = view.get_filter_fields(request)
        elif hasattr(view, 'filter_fields'):
            fields = view.filter_fields
        return fields

    def get_ordering_fields(self, request, view):
        fields = []
        if hasattr(view, 'get_ordering_fields'):
            fields = view.get_filter_fields(request)
        elif hasattr(view, 'ordering_fields'):
            fields = view.filter_fields
        return fields

    def determine_metadata(self, request, view):
        metadata = super(SimpleMetadataWithFilters, self).determine_metadata(request, view)
        filter_fields = self.get_filters_fields(request, view)
        order_fields = self.get_ordering_fields(request, view)

        meta_get = metadata.get("actions", {}).get("GET", {})
        for k, v in meta_get.items():
            if k in filter_fields:
                v["filter"] = True
            if k in order_fields:
                v["order"] = True
        return metadata
