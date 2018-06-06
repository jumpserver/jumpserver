# -*- coding: utf-8 -*-
#

from rest_framework import serializers
from .models import AssetPermission
from common.fields import StringManyToManyField


class AssetPermissionCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetPermission
        exclude = ('created_by', 'date_created')


class AssetPermissionListSerializer(serializers.ModelSerializer):
    users = StringManyToManyField(many=True, read_only=True)
    user_groups = StringManyToManyField(many=True, read_only=True)
    assets = StringManyToManyField(many=True, read_only=True)
    nodes = StringManyToManyField(many=True, read_only=True)
    system_users = StringManyToManyField(many=True, read_only=True)
    inherit = serializers.SerializerMethodField()

    class Meta:
        model = AssetPermission
        fields = '__all__'

    @staticmethod
    def get_inherit(obj):
        if hasattr(obj, 'inherit'):
            return obj.inherit
        else:
            return None


class AssetPermissionUpdateUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = AssetPermission
        fields = ['id', 'users']


class AssetPermissionUpdateAssetSerializer(serializers.ModelSerializer):

    class Meta:
        model = AssetPermission
        fields = ['id', 'assets']

