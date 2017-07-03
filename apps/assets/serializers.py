# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from django.core.cache import cache
from rest_framework import viewsets, serializers, generics
from .models import AssetGroup, Asset, IDC, AdminUser, SystemUser
from common.mixins import IDInFilterMixin
from rest_framework_bulk import BulkListSerializer, BulkSerializerMixin


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


class IDCUpdateAssetsSerializer(serializers.ModelSerializer):
    assets = serializers.PrimaryKeyRelatedField(many=True, queryset=Asset.objects.all())

    class Meta:
        model = IDC
        fields = ['id', 'assets']


class AdminUserSerializer(serializers.ModelSerializer):
    assets = serializers.PrimaryKeyRelatedField(many=True, queryset=Asset.objects.all())

    class Meta:
        model = AdminUser
        fields = '__all__'

    def get_field_names(self, declared_fields, info):
        fields = super(AdminUserSerializer, self).get_field_names(declared_fields, info)
        fields.append('assets_amount')
        return fields


class SystemUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemUser
        exclude = ('_password', '_private_key', '_public_key')

    def get_field_names(self, declared_fields, info):
        fields = super(SystemUserSerializer, self).get_field_names(declared_fields, info)
        fields.extend(['assets_amount'])
        return fields


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
    # system_users = SystemUserSerializer(many=True, read_only=True)
    # admin_user = AdminUserSerializer(many=False, read_only=True)
    hardware = serializers.SerializerMethodField()
    is_online = serializers.SerializerMethodField()

    class Meta(object):
        model = Asset
        list_serializer_class = BulkListSerializer
        fields = '__all__'

    @staticmethod
    def get_hardware(obj):
        if obj.cpu_count:
            return '{} Core {} {}'.format(obj.cpu_count*obj.cpu_cores, obj.memory, obj.disk_total)
        else:
            return ''

    @staticmethod
    def get_is_online(obj):
        hostname = obj.hostname
        if cache.get(hostname) == '1':
            return True
        elif cache.get(hostname) == '0':
            return False
        else:
            return 'Unknown'

    def get_field_names(self, declared_fields, info):
        fields = super(AssetSerializer, self).get_field_names(declared_fields, info)
        fields.extend(['get_type_display', 'get_env_display'])
        return fields


class AssetGrantedSerializer(serializers.ModelSerializer):
    system_users_granted = AssetSystemUserSerializer(many=True, read_only=True)
    is_inherited = serializers.SerializerMethodField()
    system_users_join = serializers.SerializerMethodField()

    class Meta(object):
        model = Asset
        fields = ("id", "hostname", "ip", "port", "system_users_granted", "is_inherited",
                  "is_active", "system_users_join", "comment")

    @staticmethod
    def get_is_inherited(obj):
        if getattr(obj, 'inherited', ''):
            return True
        else:
            return False

    @staticmethod
    def get_system_users_join(obj):
        return ', '.join([system_user.username for system_user in obj.system_users_granted])


class IDCSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    assets_amount = serializers.SerializerMethodField()
    assets = serializers.PrimaryKeyRelatedField(many=True, queryset=Asset.objects.all())

    class Meta:
        model = IDC
        fields = '__all__'

    @staticmethod
    def get_assets_amount(obj):
        return obj.assets.count()

    def get_field_names(self, declared_fields, info):
        fields = super(IDCSerializer, self).get_field_names(declared_fields, info)
        fields.append('assets_amount')
        return fields

