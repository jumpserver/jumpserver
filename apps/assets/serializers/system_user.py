from rest_framework import serializers

from django.utils.translation import ugettext_lazy as _

from common.serializers import AdaptedBulkListSerializer
from orgs.mixins import BulkOrgResourceModelSerializer
from ..models import SystemUser
from .base import AuthSerializer


class SystemUserSerializer(BulkOrgResourceModelSerializer):
    """
    系统用户
    """
    password = serializers.CharField(
        required=False, write_only=True, label=_('Password')
    )
    unreachable_amount = serializers.SerializerMethodField(
        label=_('Unreachable')
    )
    unreachable_assets = serializers.SerializerMethodField(
        label=_('Unreachable assets')
    )
    reachable_assets = serializers.SerializerMethodField(
        label=_('Reachable assets')
    )
    reachable_amount = serializers.SerializerMethodField(label=_('Reachable'))
    assets_amount = serializers.SerializerMethodField(label=_('Asset'))

    class Meta:
        model = SystemUser
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'name', 'username', 'login_mode', 'login_mode_display',
            'login_mode_display', 'priority', 'protocol', 'auto_push',
            'password', 'assets_amount', 'reachable_amount', 'reachable_assets',
            'unreachable_amount', 'unreachable_assets', 'cmd_filters', 'sudo',
            'shell', 'comment', 'nodes', 'assets'
        ]
        extra_kwargs = {
            'login_mode_display': {'label': _('Login mode display')},
            'created_by': {'read_only': True},
        }

    @staticmethod
    def get_unreachable_assets(obj):
        return obj.assets_unreachable

    @staticmethod
    def get_reachable_assets(obj):
        return obj.assets_reachable

    def get_unreachable_amount(self, obj):
        return len(self.get_unreachable_assets(obj))

    def get_reachable_amount(self, obj):
        return len(self.get_reachable_assets(obj))

    @staticmethod
    def get_assets_amount(obj):
        return len(obj.get_related_assets())


class SystemUserAuthSerializer(AuthSerializer):
    """
    系统用户认证信息
    """

    class Meta:
        model = SystemUser
        fields = [
            "id", "name", "username", "protocol",
            "login_mode", "password", "private_key",
        ]


class AssetSystemUserSerializer(serializers.ModelSerializer):
    """
    查看授权的资产系统用户的数据结构，这个和AssetSerializer不同，字段少
    """
    actions = serializers.SerializerMethodField()

    class Meta:
        model = SystemUser
        fields = (
            'id', 'name', 'username', 'priority',
            'protocol',  'comment', 'login_mode', 'actions',
        )

    @staticmethod
    def get_actions(obj):
        return [action.name for action in obj.actions]


class SystemUserSimpleSerializer(serializers.ModelSerializer):
    """
    系统用户最基本信息的数据结构
    """
    class Meta:
        model = SystemUser
        fields = ('id', 'name', 'username')



