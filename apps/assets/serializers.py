# -*- coding: utf-8 -*-
from django.core.cache import cache
from rest_framework import viewsets, serializers, generics
from rest_framework_bulk.serializers import BulkListSerializer

from common.mixins import BulkSerializerMixin
from .models import AssetGroup, Asset, Cluster, AdminUser, SystemUser
from .tasks import SYSTEM_USER_CONN_CACHE_KEY_PREFIX, ADMIN_USER_CONN_CACHE_KEY_PREFIX


class AssetGroupSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    assets_amount = serializers.SerializerMethodField()
    assets = serializers.PrimaryKeyRelatedField(many=True, queryset=Asset.objects.all())

    class Meta:
        model = AssetGroup
        list_serializer_class = BulkListSerializer
        fields = ['id', 'name', 'comment', 'assets_amount', 'assets']

    @staticmethod
    def get_assets_amount(obj):
        return obj.assets.count()


class AssetUpdateGroupSerializer(serializers.ModelSerializer):
    groups = serializers.PrimaryKeyRelatedField(many=True, queryset=AssetGroup.objects.all())

    class Meta:
        model = Asset
        fields = ['id', 'groups']


class AssetUpdateSystemUserSerializer(serializers.ModelSerializer):
    system_users = serializers.PrimaryKeyRelatedField(many=True, queryset=SystemUser.objects.all())

    class Meta:
        model = Asset
        fields = ['id', 'system_users']


class AssetGroupUpdateSerializer(serializers.ModelSerializer):
    """update the asset group, and add or delete the asset to the group"""
    assets = serializers.PrimaryKeyRelatedField(many=True, queryset=Asset.objects.all())

    class Meta:
        model = AssetGroup
        fields = ['id', 'assets']


class AssetGroupUpdateSystemUserSerializer(serializers.ModelSerializer):
    system_users = serializers.PrimaryKeyRelatedField(many=True, queryset=SystemUser.objects.all())

    class Meta:
        model = AssetGroup
        fields = ['id', 'system_users']


class ClusterUpdateAssetsSerializer(serializers.ModelSerializer):
    assets = serializers.PrimaryKeyRelatedField(many=True, queryset=Asset.objects.all())

    class Meta:
        model = Cluster
        fields = ['id', 'assets']


class AdminUserSerializer(serializers.ModelSerializer):
    assets_amount = serializers.SerializerMethodField()
    unreachable_amount = serializers.SerializerMethodField()

    class Meta:
        model = AdminUser
        fields = '__all__'

    @staticmethod
    def get_unreachable_amount(obj):
        data = cache.get(ADMIN_USER_CONN_CACHE_KEY_PREFIX + obj.name)
        if data:
            return len(data.get('dark'))
        else:
            return 'Unknown'

    @staticmethod
    def get_assets_amount(obj):
        amount = 0
        clusters = obj.cluster_set.all()
        for cluster in clusters:
            amount += len(cluster.assets.all())
        return amount


class SystemUserSerializer(serializers.ModelSerializer):
    unreachable_amount = serializers.SerializerMethodField()
    assets_amount = serializers.SerializerMethodField()

    class Meta:
        model = SystemUser
        exclude = ('_password', '_private_key', '_public_key')

    @staticmethod
    def get_unreachable_amount(obj):
        data = cache.get(SYSTEM_USER_CONN_CACHE_KEY_PREFIX + obj.name)
        if data:
            return len(data.get('dark'))
        else:
            return "Unknown"

    @staticmethod
    def get_assets_amount(obj):
        amount = 0
        for cluster in obj.cluster.all():
            amount += cluster.assets.all().count()
        return amount


class AssetSystemUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemUser
        fields = ('id', 'name', 'username', 'protocol', 'auth_method', 'comment')


class SystemUserUpdateAssetsSerializer(serializers.ModelSerializer):
    assets = serializers.PrimaryKeyRelatedField(many=True, queryset=Asset.objects.all())

    class Meta:
        model = SystemUser
        fields = ['id', 'assets']


class SystemUserUpdateAssetGroupSerializer(serializers.ModelSerializer):
    asset_groups = serializers.PrimaryKeyRelatedField(many=True, queryset=AssetGroup.objects.all())

    class Meta:
        model = SystemUser
        fields = ['id', 'asset_groups']


class SystemUserSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemUser
        fields = ('id', 'name', 'username')


class AssetSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    class Meta(object):
        model = Asset
        list_serializer_class = BulkListSerializer
        fields = '__all__'
        validators = []  # If not set to [], partial bulk update will be error

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields.extend([
            'get_type_display', 'get_env_display',
            'hardware_info', 'is_connective',
        ])
        return fields


class AssetGrantedSerializer(serializers.ModelSerializer):
    system_users_granted = AssetSystemUserSerializer(many=True, read_only=True)
    is_inherited = serializers.SerializerMethodField()
    system_users_join = serializers.SerializerMethodField()

    class Meta(object):
        model = Asset
        fields = ("id", "hostname", "ip", "port", "system_users_granted",
                  "is_inherited", "is_active", "system_users_join", "comment")

    @staticmethod
    def get_is_inherited(obj):
        if getattr(obj, 'inherited', ''):
            return True
        else:
            return False

    @staticmethod
    def get_system_users_join(obj):
        return ', '.join([system_user.username for system_user in obj.system_users_granted])


class MyAssetGrantedSerializer(AssetGrantedSerializer):
    """Remove ip and port from asset for security"""

    class Meta(object):
        model = Asset
        fields = ("id", "hostname", "system_users_granted", "is_inherited",
                  "is_active", "system_users_join", "comment")


class ClusterSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    assets_amount = serializers.SerializerMethodField()
    admin_user_name = serializers.SerializerMethodField()
    assets = serializers.PrimaryKeyRelatedField(many=True, queryset=Asset.objects.all())

    class Meta:
        model = Cluster
        fields = '__all__'

    @staticmethod
    def get_assets_amount(obj):
        return obj.assets.count()

    @staticmethod
    def get_admin_user_name(obj):
        return obj.admin_user.name


class AssetGroupGrantedSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    assets_granted = AssetGrantedSerializer(many=True, read_only=True)
    assets_amount = serializers.SerializerMethodField()

    class Meta:
        model = AssetGroup
        list_serializer_class = BulkListSerializer
        fields = '__all__'

    @staticmethod
    def get_assets_amount(obj):
        return len(obj.assets_granted)


class MyAssetGroupGrantedSerializer(serializers.ModelSerializer):
    assets_granted = MyAssetGrantedSerializer(many=True, read_only=True)
    assets_amount = serializers.SerializerMethodField()

    class Meta:
        model = AssetGroup
        list_serializer_class = BulkListSerializer
        fields = '__all__'

    @staticmethod
    def get_assets_amount(obj):
        return len(obj.assets_granted)
