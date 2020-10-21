# -*- coding: utf-8 -*-
#

from rest_framework import serializers

from django.db.models import Count
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from perms.models import ApplicationPermission

__all__ = [
    'ApplicationPermissionSerializer'
]


class ApplicationPermissionSerializer(BulkOrgResourceModelSerializer):
    is_valid = serializers.BooleanField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = ApplicationPermission
        mini_fields = ['id', 'name']
        small_fields = mini_fields + [
            'is_active', 'is_expired', 'is_valid', 'created_by', 'date_created',
            'date_expired', 'date_start', 'comment'
        ]
        m2m_fields = [
            'users', 'user_groups', 'applications', 'system_users',
            'users_amount', 'user_groups_amount', 'applications_amount', 'system_users_amount',
        ]
        fields = small_fields + m2m_fields
        read_only_fields = ['created_by', 'date_created']

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('users', 'user_groups', 'applications', 'system_users')
        return queryset

