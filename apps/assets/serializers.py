# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from rest_framework import viewsets, serializers,generics
from .models import AssetGroup, Asset, IDC, AssetExtend, AdminUser, SystemUser
from common.mixins import BulkDeleteApiMixin
from rest_framework_bulk import BulkListSerializer, BulkSerializerMixin


class AssetGroupSerializer(serializers.ModelSerializer):
    assets_amount = serializers.SerializerMethodField()
    # assets = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = AssetGroup

    @staticmethod
    def get_assets_amount(obj):
        return obj.assets.count()


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminUser

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
        fields.append('assets_amount')
        return fields


class AssetSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    # system_users = SystemUserSerializer(many=True, read_only=True)
    # admin_user = AdminUserSerializer(many=False, read_only=True)
    hardware = serializers.SerializerMethodField()
    type_display = serializers.SerializerMethodField()

    class Meta(object):
        model = Asset
        list_serializer_class = BulkListSerializer

    @staticmethod
    def get_hardware(obj):
        return '%s %s %s' % (obj.cpu, obj.memory, obj.disk)

    @staticmethod
    def get_type_display(obj):
        if obj.type:
            return obj.type.value
        else:
            return ''


class AssetGrantedSerializer(serializers.ModelSerializer):
    system_users = SystemUserSerializer(many=True, read_only=True)
    is_inherited = serializers.SerializerMethodField()
    system_users_join = serializers.SerializerMethodField()

    class Meta(object):
        model = Asset
        fields = ("id", "hostname", "ip", "port", "system_users", "is_inherited",
                  "is_active", "system_users_join", "comment")

    @staticmethod
    def get_is_inherited(obj):
        if getattr(obj, 'inherited', ''):
            return True
        else:
            return False

    @staticmethod
    def get_system_users_join(obj):
        return ', '.join([system_user.username for system_user in obj.system_users.all()])


class IDCSerializer(serializers.ModelSerializer):
    assets_amount = serializers.SerializerMethodField()

    class Meta:
        model = IDC

    @staticmethod
    def get_assets_amount(obj):
        return obj.assets.count()

    def get_field_names(self, declared_fields, info):
        fields = super(IDCSerializer, self).get_field_names(declared_fields, info)
        fields.append('assets_amount')
        return fields
