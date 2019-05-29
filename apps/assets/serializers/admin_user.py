# -*- coding: utf-8 -*-
#
from django.core.cache import cache
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from common.serializers import AdaptedBulkListSerializer

from ..models import Node, AdminUser
from ..const import ADMIN_USER_CONN_CACHE_KEY

from .base import AuthSerializer


class AdminUserSerializer(serializers.ModelSerializer):
    """
    管理用户
    """
    password = serializers.CharField(
        required=False, write_only=True, label=_('Password')
    )
    unreachable_amount = serializers.SerializerMethodField(label=_('Unreachable'))
    assets_amount = serializers.SerializerMethodField(label=_('Asset'))
    reachable_amount = serializers.SerializerMethodField(label=_('Reachable'))

    class Meta:
        list_serializer_class = AdaptedBulkListSerializer
        model = AdminUser
        fields = [
            'id', 'org_id', 'name', 'username', 'assets_amount',
            'reachable_amount', 'unreachable_amount', 'password', 'comment',
            'date_created', 'date_updated', 'become', 'become_method',
            'become_user', 'created_by',
        ]

        extra_kwargs = {
            'date_created': {'label': _('Date created')},
            'date_updated': {'label': _('Date updated')},
            'become': {'read_only': True}, 'become_method': {'read_only': True},
            'become_user': {'read_only': True}, 'created_by': {'read_only': True}
        }

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        return [f for f in fields if not f.startswith('_')]

    @staticmethod
    def get_unreachable_amount(obj):
        data = cache.get(ADMIN_USER_CONN_CACHE_KEY.format(obj.name))
        if data:
            return len(data.get('dark'))
        else:
            return 0

    @staticmethod
    def get_reachable_amount(obj):
        data = cache.get(ADMIN_USER_CONN_CACHE_KEY.format(obj.name))
        if data:
            return len(data.get('contacted'))
        else:
            return 0

    @staticmethod
    def get_assets_amount(obj):
        return obj.assets_amount


class AdminUserAuthSerializer(AuthSerializer):

    class Meta:
        model = AdminUser
        fields = ['password', 'private_key']


class ReplaceNodeAdminUserSerializer(serializers.ModelSerializer):
    """
    管理用户更新关联到的集群
    """
    nodes = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Node.objects.all()
    )

    class Meta:
        model = AdminUser
        fields = ['id', 'nodes']


class TaskIDSerializer(serializers.Serializer):
    task = serializers.CharField(read_only=True)
