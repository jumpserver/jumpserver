from rest_framework import serializers

from django.utils.translation import ugettext_lazy as _

from common.serializers import AdaptedBulkListSerializer

from ..models import SystemUser, Asset
from .base import AuthSerializer


class SystemUserSerializer(serializers.ModelSerializer):
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
            'id', 'org_id', 'name', 'username', 'login_mode',
            'login_mode_display', 'priority', 'protocol', 'auto_push',
            'password', 'assets_amount', 'reachable_amount', 'reachable_assets',
            'unreachable_amount', 'unreachable_assets', 'cmd_filters', 'sudo',
            'shell', 'comment', 'nodes', 'assets'
        ]
        extra_kwargs = {
            'login_mode_display': {'label': _('Login mode display')},
            'created_by': {'read_only': True}, 'nodes': {'read_only': True},
            'assets': {'read_only': True}
        }

    def get_field_names(self, declared_fields, info):
        fields = super(SystemUserSerializer, self).get_field_names(declared_fields, info)
        fields.extend([
            'login_mode_display',
        ])
        return fields

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



