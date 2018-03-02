# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from common.utils import get_object_or_none
from common.fields import StringIDField
from .models import AssetPermission, NodePermission


class AssetPermissionCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NodePermission
        fields = [
            'id', 'node', 'user_group', 'system_user',
            'is_active', 'date_expired'
        ]


class AssetPermissionListSerializer(serializers.ModelSerializer):
    node = StringIDField(read_only=True)
    user_group = StringIDField(read_only=True)
    system_user = StringIDField(read_only=True)

    class Meta:
        model = NodePermission
        fields = '__all__'


class AssetPermissionUpdateUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = AssetPermission
        fields = ['id', 'users']


class AssetPermissionUpdateAssetSerializer(serializers.ModelSerializer):

    class Meta:
        model = AssetPermission
        fields = ['id', 'assets']


class UserAssetPermissionCreateUpdateSerializer(AssetPermissionCreateUpdateSerializer):
    is_inherited = serializers.SerializerMethodField()

    @staticmethod
    def get_is_inherited(obj):
        if getattr(obj, 'inherited', ''):
            return True
        else:
            return False

