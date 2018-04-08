# -*- coding: utf-8 -*-
#

from rest_framework import serializers
from .models import AssetPermission


class AssetPermissionCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetPermission
        exclude = ('id', 'create_by', 'date_created')


class AssetPermissionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetPermission
        fields = '__all__'


class AssetPermissionUpdateUserSerializer(serializers.ModelSerializer):

    class Meta:
        model = AssetPermission
        fields = ['id', 'users']


class AssetPermissionUpdateAssetSerializer(serializers.ModelSerializer):

    class Meta:
        model = AssetPermission
        fields = ['id', 'assets']

