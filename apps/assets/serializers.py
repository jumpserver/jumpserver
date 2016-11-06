# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from rest_framework import viewsets, serializers,generics
from .models import AssetGroup, Asset, IDC, AssetExtend, AdminUser, SystemUser
from common.mixins import BulkDeleteApiMixin
from rest_framework_bulk import BulkListSerializer, BulkSerializerMixin


class AssetBulkUpdateSerializer(BulkSerializerMixin, serializers.ModelSerializer):
    # group_display = serializers.SerializerMethodField()
    # active_display = serializers.SerializerMethodField()
    #groups = serializers.PrimaryKeyRelatedField(many=True, queryset=AssetGroup.objects.all())

    class Meta(object):
        model = Asset
        list_serializer_class = BulkListSerializer
        fields = ('id', 'port', 'idc')

    # def get_group_display(self, obj):
    #     return " ".join([group.name for group in obj.groups.all()])
    #
    # def get_active_display(self, obj):
    #     # TODO: user ative state
    #     return not (obj.is_expired and obj.is_active)


class AssetGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetGroup


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset


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

    def get_field_names(self, declared_fields, info):
        fields = super(SystemUserSerializer, self).get_field_names(declared_fields, info)
        fields.append('assets_amount')
        return fields


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
