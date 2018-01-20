# -*- coding: utf-8 -*-
from django.core.cache import cache
from rest_framework import serializers
from rest_framework_bulk.serializers import BulkListSerializer

from common.mixins import BulkSerializerMixin
from .models import AssetGroup, Asset, Cluster, AdminUser, SystemUser
from .const import ADMIN_USER_CONN_CACHE_KEY, SYSTEM_USER_CONN_CACHE_KEY


class AssetGroupSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    """
    资产组序列化数据模型
    """
    assets_amount = serializers.SerializerMethodField()
    assets = serializers.PrimaryKeyRelatedField(many=True, queryset=Asset.objects.all())

    class Meta:
        model = AssetGroup
        list_serializer_class = BulkListSerializer
        fields = ['id', 'name', 'comment', 'assets_amount', 'assets']

    @staticmethod
    def get_assets_amount(obj):
        return obj.asset_count


class AssetUpdateSystemUserSerializer(serializers.ModelSerializer):
    """
    资产更新其系统用户请求的数据结构定义
    """
    system_users = serializers.PrimaryKeyRelatedField(many=True, queryset=SystemUser.objects.all())

    class Meta:
        model = Asset
        fields = ['id', 'system_users']


class GroupUpdateAssetsSerializer(serializers.ModelSerializer):
    """
    资产组更新需要的数据结构
    """
    assets = serializers.PrimaryKeyRelatedField(many=True, queryset=Asset.objects.all())

    class Meta:
        model = AssetGroup
        fields = ['id', 'assets']


class ClusterUpdateAssetsSerializer(serializers.ModelSerializer):
    """
    集群更新资产数据结构
    """
    assets = serializers.PrimaryKeyRelatedField(many=True, queryset=Asset.objects.all())

    class Meta:
        model = Cluster
        fields = ['id', 'assets']


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


class SystemUserSerializer(serializers.ModelSerializer):
    """
    系统用户
    """
    unreachable_amount = serializers.SerializerMethodField()
    reachable_amount = serializers.SerializerMethodField()
    unreachable_assets = serializers.SerializerMethodField()
    reachable_assets = serializers.SerializerMethodField()
    assets_amount = serializers.SerializerMethodField()

    class Meta:
        model = SystemUser
        exclude = ('_password', '_private_key', '_public_key')

    @staticmethod
    def get_unreachable_assets(obj):
        return obj.unreachable_assets

    @staticmethod
    def get_reachable_assets(obj):
        return obj.reachable_assets

    def get_unreachable_amount(self, obj):
        return len(self.get_unreachable_assets(obj))

    def get_reachable_amount(self, obj):
        return len(self.get_reachable_assets(obj))

    @staticmethod
    def get_assets_amount(obj):
        amount = 0
        for cluster in obj.cluster.all():
            amount += cluster.assets.all().count()
        return amount


class AdminUserUpdateClusterSerializer(serializers.ModelSerializer):
    """
    管理用户更新关联到的集群
    """
    clusters = serializers.PrimaryKeyRelatedField(many=True, queryset=Cluster.objects.all())

    class Meta:
        model = AdminUser
        fields = ['id', 'clusters']


class AssetSystemUserSerializer(serializers.ModelSerializer):
    """
    查看授权的资产系统用户的数据结构，这个和AssetSerializer不同，字段少
    """
    class Meta:
        model = SystemUser
        fields = ('id', 'name', 'username', 'priority', 'protocol',  'comment',)


class SystemUserSimpleSerializer(serializers.ModelSerializer):
    """
    系统用户最基本信息的数据结构
    """
    class Meta:
        model = SystemUser
        fields = ('id', 'name', 'username')


class AssetSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    """
    资产的数据结构
    """
    cluster_name = serializers.SerializerMethodField()

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

    @staticmethod
    def get_cluster_name(obj):
        return obj.cluster.name


class AssetGrantedSerializer(serializers.ModelSerializer):
    """
    被授权资产的数据结构
    """
    system_users_granted = AssetSystemUserSerializer(many=True, read_only=True)
    is_inherited = serializers.SerializerMethodField()
    system_users_join = serializers.SerializerMethodField()

    class Meta(object):
        model = Asset
        fields = (
            "id", "hostname", "ip", "port", "system_users_granted",
            "is_inherited", "is_active", "system_users_join", "os",
            "platform", "comment"
        )

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
    """
    普通用户获取授权的资产定义的数据结构
    """

    class Meta(object):
        model = Asset
        fields = (
            "id", "hostname", "system_users_granted",
            "is_inherited", "is_active", "system_users_join",
            "os", "platform", "comment",
        )


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


class AssetGroupGrantedSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    """
    授权资产组
    """
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
    """
    普通用户授权资产组结构
    """
    assets_granted = MyAssetGrantedSerializer(many=True, read_only=True)
    assets_amount = serializers.SerializerMethodField()

    class Meta:
        model = AssetGroup
        list_serializer_class = BulkListSerializer
        fields = '__all__'

    @staticmethod
    def get_assets_amount(obj):
        return len(obj.assets_granted)
