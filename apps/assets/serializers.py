# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _
from rest_framework import viewsets, serializers,generics
from .models import AssetGroup, Asset, IDC, AssetExtend, AdminUser, SystemUser
from common.mixins import BulkDeleteApiMixin
from rest_framework_bulk import BulkListSerializer, BulkSerializerMixin


class AssetSerializer(BulkSerializerMixin, serializers.ModelSerializer):

    class Meta(object):
        model = Asset
        list_serializer_class = BulkListSerializer


class AssetGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetGroup


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
