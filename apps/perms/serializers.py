# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from common.utils import get_object_or_none
from .models import AssetPermission
from .hands import User


class AssetPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssetPermission
        fields = '__all__'


class UserAssetPermissionSerializer(AssetPermissionSerializer):
    is_inherited = serializers.SerializerMethodField()

    @staticmethod
    def get_is_inherited(obj):
        if getattr(obj, 'inherited', ''):
            return True
        else:
            return False

