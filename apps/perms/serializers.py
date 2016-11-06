# -*- coding: utf-8 -*-
#

from rest_framework  import serializers
from .models import AssetPermission


class AssetPermissionSerializer(serializers.ModelSerializer):
    # users_amount = serializers.SerializerMethodField()
    # user_groups_amount = serializers.SerializerMethodField()
    # assets_amount = serializers.SerializerMethodField()
    # asset_groups_amount = serializers.SerializerMethodField()

    class Meta:
        model = AssetPermission
        fields = ['id', 'name', 'users', 'user_groups', 'assets', 'asset_groups',
                  'system_users', 'is_active', 'comment', 'date_expired']

    # @staticmethod
    # def get_users_amount(obj):
    #     return obj.users.count()
    #
    # @staticmethod
    # def get_user_groups_amount(obj):
    #     return obj.user_groups.count()
    #
    # @staticmethod
    # def get_assets_amount(obj):
    #     return obj.assets.count()
    #
    # @staticmethod
    # def get_asset_groups_amount(obj):
    #     return obj.asset_groups.count()

