# coding: utf-8
#
from django.db.models import Count
from rest_framework import serializers

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .. import models

__all__ = [
    'K8sAppPermissionSerializer', 'K8sAppPermissionListSerializer'
]


class AmountMixin:
    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.annotate(
            users_amount=Count('users', distinct=True), user_groups_amount=Count('user_groups', distinct=True),
            k8s_apps_amount=Count('k8s_apps', distinct=True),
            system_users_amount=Count('system_users', distinct=True)
        )
        return queryset


class K8sAppPermissionSerializer(AmountMixin, BulkOrgResourceModelSerializer):
    class Meta:
        model = models.K8sAppPermission
        fields = [
            'id', 'name', 'users', 'user_groups', 'k8s_apps', 'system_users',
            'comment', 'is_active', 'date_start', 'date_expired', 'is_valid',
            'created_by', 'date_created', 'users_amount', 'user_groups_amount',
            'k8s_apps_amount', 'system_users_amount',
        ]
        read_only_fields = [
            'created_by', 'date_created', 'users_amount', 'user_groups_amount',
            'k8s_apps_amount', 'system_users_amount', 'id'
        ]


class K8sAppPermissionListSerializer(AmountMixin, BulkOrgResourceModelSerializer):
    is_expired = serializers.BooleanField()

    class Meta:
        model = models.K8sAppPermission
        fields = [
            'id', 'name', 'comment', 'is_active', 'users_amount', 'user_groups_amount',
            'date_start', 'date_expired', 'is_valid', 'k8s_apps_amount', 'system_users_amount',
            'created_by', 'date_created', 'is_expired'
        ]
