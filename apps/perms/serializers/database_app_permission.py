# coding: utf-8
#
from django.db.models import Count
from rest_framework import serializers

from common.fields import StringManyToManyField
from common.serializers import AdaptedBulkListSerializer
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .. import models

__all__ = [
    'DatabaseAppPermissionSerializer', 'DatabaseAppPermissionListSerializer'
]


class AmountMixin:
    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.annotate(
            users_amount=Count('users', distinct=True), user_groups_amount=Count('user_groups', distinct=True),
            database_apps_amount=Count('database_apps', distinct=True),
            system_users_amount=Count('system_users', distinct=True)
        )
        return queryset


class DatabaseAppPermissionSerializer(AmountMixin, BulkOrgResourceModelSerializer):
    class Meta:
        model = models.DatabaseAppPermission
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'name', 'users', 'user_groups', 'database_apps', 'system_users',
            'comment', 'is_active', 'date_start', 'date_expired', 'is_valid',
            'created_by', 'date_created', 'users_amount', 'user_groups_amount',
            'database_apps_amount', 'system_users_amount',
        ]
        read_only_fields = [
            'created_by', 'date_created', 'users_amount', 'user_groups_amount',
            'database_apps_amount', 'system_users_amount',
        ]


class DatabaseAppPermissionListSerializer(AmountMixin, BulkOrgResourceModelSerializer):
    is_expired = serializers.BooleanField()

    class Meta:
        model = models.DatabaseAppPermission
        fields = [
            'id', 'name', 'comment', 'is_active', 'users_amount', 'user_groups_amount',
            'date_start', 'date_expired', 'is_valid', 'database_apps_amount', 'system_users_amount',
            'created_by', 'date_created', 'is_expired'
        ]
