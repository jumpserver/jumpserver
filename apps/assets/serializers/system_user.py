import re
from rest_framework import serializers

from django.utils.translation import ugettext_lazy as _

from common.serializers import AdaptedBulkListSerializer
from common.mixins.serializers import BulkSerializerMixin
from common.utils import ssh_pubkey_gen
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from assets.models import Node
from ..models import SystemUser
from ..const import (
    GENERAL_FORBIDDEN_SPECIAL_CHARACTERS_PATTERN,
    GENERAL_FORBIDDEN_SPECIAL_CHARACTERS_ERROR_MSG
)
from .base import AuthSerializer, AuthSerializerMixin

__all__ = [
    'SystemUserSerializer', 'SystemUserAuthSerializer',
    'SystemUserSimpleSerializer', 'SystemUserAssetRelationSerializer',
    'SystemUserNodeRelationSerializer',
]


class SystemUserSerializer(AuthSerializerMixin, BulkOrgResourceModelSerializer):
    """
    系统用户
    """
    auto_generate_key = serializers.BooleanField(initial=True, required=False, write_only=True)

    class Meta:
        model = SystemUser
        list_serializer_class = AdaptedBulkListSerializer
        fields = [
            'id', 'name', 'username', 'password', 'public_key', 'private_key',
            'login_mode', 'login_mode_display', 'priority', 'protocol',
            'auto_push', 'cmd_filters', 'sudo', 'shell', 'comment',
            'assets_amount', 'nodes_amount', 'auto_generate_key'
        ]
        extra_kwargs = {
            'password': {"write_only": True},
            'public_key': {"write_only": True},
            'private_key': {"write_only": True},
            'nodes_amount': {'label': _('Node')},
            'assets_amount': {'label': _('Asset')},
            'login_mode_display': {'label': _('Login mode display')},
            'created_by': {'read_only': True},
        }

    @staticmethod
    def validate_name(name):
        pattern = GENERAL_FORBIDDEN_SPECIAL_CHARACTERS_PATTERN
        res = re.search(pattern, name)
        if res is not None:
            msg = GENERAL_FORBIDDEN_SPECIAL_CHARACTERS_ERROR_MSG
            raise serializers.ValidationError(msg)
        return name

    def validate_auto_push(self, value):
        login_mode = self.initial_data.get("login_mode")
        protocol = self.initial_data.get("protocol")

        if login_mode == SystemUser.LOGIN_MANUAL or \
                protocol in [SystemUser.PROTOCOL_TELNET,
                             SystemUser.PROTOCOL_VNC]:
            value = False
        return value

    def validate_auto_generate_key(self, value):
        login_mode = self.initial_data.get("login_mode")
        protocol = self.initial_data.get("protocol")

        if self.context["request"].method.lower() != "post":
            value = False
        elif self.instance:
            value = False
        elif login_mode == SystemUser.LOGIN_MANUAL:
            value = False
        elif protocol in [SystemUser.PROTOCOL_TELNET, SystemUser.PROTOCOL_VNC]:
            value = False
        return value

    def validate_username(self, username):
        if username:
            return username
        login_mode = self.initial_data.get("login_mode")
        protocol = self.initial_data.get("protocol")
        if login_mode == SystemUser.LOGIN_AUTO and \
                protocol != SystemUser.PROTOCOL_VNC:
            msg = _('* Automatic login mode must fill in the username.')
            raise serializers.ValidationError(msg)
        return username

    def validate_password(self, password):
        super().validate_password(password)
        auto_gen_key = self.initial_data.get("auto_generate_key", False)
        private_key = self.initial_data.get("private_key")
        login_mode = self.initial_data.get("login_mode")
        if not self.instance and not auto_gen_key and not password and \
                not private_key and login_mode == SystemUser.LOGIN_AUTO:
            raise serializers.ValidationError(_("Password or private key required"))
        return password

    def validate(self, attrs):
        username = attrs.get("username", "manual")
        protocol = attrs.get("protocol")
        auto_gen_key = attrs.get("auto_generate_key", False)
        if auto_gen_key:
            password = SystemUser.gen_password()
            attrs["password"] = password
            if protocol == SystemUser.PROTOCOL_SSH:
                private_key, public_key = SystemUser.gen_key(username)
                attrs["private_key"] = private_key
                attrs["public_key"] = public_key
                # 如果设置了private key，没有设置public key则生成
        elif attrs.get("private_key", None):
            private_key = attrs["private_key"]
            password = attrs.get("password")
            public_key = ssh_pubkey_gen(private_key, password=password,
                                        username=username)
            attrs["public_key"] = public_key
        attrs.pop("auto_generate_key", None)
        return attrs

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('cmd_filters', 'nodes')
        return queryset


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


class SystemUserSimpleSerializer(serializers.ModelSerializer):
    """
    系统用户最基本信息的数据结构
    """
    class Meta:
        model = SystemUser
        fields = ('id', 'name', 'username')


class RelationMixin(BulkSerializerMixin, serializers.Serializer):
    systemuser_display = serializers.ReadOnlyField()

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields.extend(['systemuser', "systemuser_display"])
        return fields

    class Meta:
        list_serializer_class = AdaptedBulkListSerializer


class SystemUserAssetRelationSerializer(RelationMixin, serializers.ModelSerializer):
    asset_display = serializers.ReadOnlyField()

    class Meta(RelationMixin.Meta):
        model = SystemUser.assets.through
        fields = [
            'id', "asset", "asset_display",
        ]


class SystemUserNodeRelationSerializer(RelationMixin, serializers.ModelSerializer):
    node_display = serializers.SerializerMethodField()

    class Meta(RelationMixin.Meta):
        model = SystemUser.nodes.through
        fields = [
            'id', 'node', "node_display",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tree = Node.tree()

    def get_node_display(self, obj):
        if hasattr(obj, 'node_key'):
            return self.tree.get_node_full_tag(obj.node_key)
        else:
            return obj.node.full_value
