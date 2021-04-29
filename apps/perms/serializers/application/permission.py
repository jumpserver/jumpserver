# -*- coding: utf-8 -*-
#

from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from perms.models import ApplicationPermission

__all__ = [
    'ApplicationPermissionSerializer'
]


class ApplicationPermissionSerializer(BulkOrgResourceModelSerializer):
    category_display = serializers.ReadOnlyField(source='get_category_display', label=_('Category'))
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_('Type'))
    is_valid = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = ApplicationPermission
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'category', 'category_display', 'type', 'type_display', 'is_active', 'is_expired',
            'is_valid', 'created_by', 'date_created', 'date_expired', 'date_start', 'comment'
        ]
        fields_m2m = [
            'users', 'user_groups', 'applications', 'system_users',
            'users_amount', 'user_groups_amount', 'applications_amount', 'system_users_amount',
        ]
        fields = fields_small + fields_m2m
        read_only_fields = ['created_by', 'date_created']

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('users', 'user_groups', 'applications', 'system_users')
        return queryset

    def validate_applications(self, applications):
        if self.instance:
            permission_type = self.instance.type
        else:
            permission_type = self.initial_data['type']

        other_type_applications = [
            application for application in applications
            if application.type != permission_type
        ]
        if len(other_type_applications) > 0:
            error = _(
                'The application list contains applications '
                'that are different from the permission type. ({})'
            ).format(', '.join([application.name for application in other_type_applications]))
            raise serializers.ValidationError(error)
        return applications
