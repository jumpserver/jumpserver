#  coding: utf-8
#
from rest_framework import serializers
from django.db.models import Count

from common.serializers import AdaptedBulkListSerializer
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import RemoteAppPermission


__all__ = [
    'RemoteAppPermissionSerializer',
    'RemoteAppPermissionUpdateUserSerializer',
    'RemoteAppPermissionUpdateRemoteAppSerializer',
]


class RemoteAppPermissionSerializer(BulkOrgResourceModelSerializer):
    class Meta:
        model = RemoteAppPermission
        list_serializer_class = AdaptedBulkListSerializer
        mini_fields = ['id', 'name']
        small_fields = mini_fields + [
            'comment', 'is_active', 'date_start', 'date_expired', 'is_valid',
            'created_by', 'date_created'
        ]
        m2m_fields = [
            'users', 'user_groups', 'remote_apps', 'system_users',
            'users_amount', 'user_groups_amount', 'remote_apps_amount',
            'system_users_amount'
        ]
        fields = small_fields + m2m_fields
        read_only_fields = ['created_by', 'date_created']

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.annotate(
            users_amount=Count('users', distinct=True), user_groups_amount=Count('user_groups', distinct=True),
            remote_apps_amount=Count('remote_apps', distinct=True),  system_users_amount=Count('system_users', distinct=True)
        )
        return queryset


class RemoteAppPermissionUpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = RemoteAppPermission
        fields = ['id', 'users']


class RemoteAppPermissionUpdateRemoteAppSerializer(serializers.ModelSerializer):
    class Meta:
        model = RemoteAppPermission
        fields = ['id', 'remote_apps']
