# -*- coding: utf-8 -*-
#
from django.core.cache import cache
from rest_framework import serializers

from ..models import Node, AdminUser
from ..const import ADMIN_USER_CONN_CACHE_KEY

from .base import AuthSerializer


class AdminUserSerializer(serializers.ModelSerializer):
    """
    管理用户
    """
    assets_amount = serializers.SerializerMethodField()
    unreachable_amount = serializers.SerializerMethodField()
    reachable_amount = serializers.SerializerMethodField()

    class Meta:
        model = AdminUser
        fields = '__all__'

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
        many=True, queryset = Node.objects.all()
    )

    class Meta:
        model = AdminUser
        fields = ['id', 'nodes']



