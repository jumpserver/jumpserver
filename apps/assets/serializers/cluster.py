# -*- coding: utf-8 -*-
#

from rest_framework import serializers
from common.mixins import BulkSerializerMixin
from ..models import Asset, Cluster


class ClusterUpdateAssetsSerializer(serializers.ModelSerializer):
    """
    集群更新资产数据结构
    """
    assets = serializers.PrimaryKeyRelatedField(many=True, queryset=Asset.objects.all())

    class Meta:
        model = Cluster
        fields = ['id', 'assets']


class ClusterSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    """
    cluster
    """
    assets_amount = serializers.SerializerMethodField()
    admin_user_name = serializers.SerializerMethodField()
    assets = serializers.PrimaryKeyRelatedField(many=True, queryset=Asset.objects.all())
    system_users = serializers.SerializerMethodField()

    class Meta:
        model = Cluster
        fields = '__all__'

    @staticmethod
    def get_assets_amount(obj):
        return obj.assets.count()

    @staticmethod
    def get_admin_user_name(obj):
        try:
            return obj.admin_user.name
        except AttributeError:
            return ''

    @staticmethod
    def get_system_users(obj):
        return ', '.join(obj.name for obj in obj.systemuser_set.all())
