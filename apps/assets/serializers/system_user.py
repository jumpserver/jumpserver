from collections import OrderedDict
from rest_framework import serializers

from django.utils.translation import ugettext_lazy as _

from common.serializers import AdaptedBulkListSerializer
from common.utils import ssh_pubkey_gen
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import SystemUser
from .base import AuthSerializer, AuthSerializerMixin, UnionValidateSerializerMixin


class SystemUserSerializer(AuthSerializerMixin,
                           UnionValidateSerializerMixin,
                           BulkOrgResourceModelSerializer):
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
            'auto_push', 'cmd_filters', 'sudo', 'shell', 'comment', 'nodes',
            'assets_amount', 'auto_generate_key'
        ]
        extra_kwargs = {
            'password': {"write_only": True},
            'public_key': {"write_only": True},
            'private_key': {"write_only": True},
            'assets_amount': {'label': _('Asset')},
            'login_mode_display': {'label': _('Login mode display')},
            'created_by': {'read_only': True},
        }

    def get_final_auto_generate_key(self, value, attrs):
        login_mode = attrs.get("login_mode")
        protocol = attrs.get("protocol")
        if self.context["request"].method.lower() != "post":
            value = False
        elif self.instance:
            value = False
        elif login_mode == SystemUser.LOGIN_MANUAL:
            value = False
        elif protocol in [SystemUser.PROTOCOL_TELNET, SystemUser.PROTOCOL_VNC]:
            value = False
        return value

    @staticmethod
    def get_final_auto_push(value, attrs):
        login_mode = attrs.get("login_mode")
        protocol = attrs.get("protocol")
        if login_mode == SystemUser.LOGIN_MANUAL:
            value = False
        if protocol in [SystemUser.PROTOCOL_TELNET, SystemUser.PROTOCOL_VNC]:
            value = False
        return value

    @staticmethod
    def union_validate_username(username, attrs):
        if username:
            return username

        login_mode = attrs.get('login_mode')
        protocol = attrs.get('protocol')
        if login_mode == SystemUser.LOGIN_AUTO and protocol != SystemUser.PROTOCOL_VNC:
            msg = _('* Automatic login mode must fill in the username.')
            raise serializers.ValidationError(msg)
        return username

    def union_validate_password(self, password, attrs):
        private_key = attrs.get("private_key")
        login_mode = attrs.get("login_mode")
        auto_gen_key = attrs.get("auto_generate_key", False)
        if not self.instance \
                and login_mode == SystemUser.LOGIN_AUTO \
                and not auto_gen_key \
                and not password \
                and not private_key:
            msg = _("Password or private key required")
            raise serializers.ValidationError(msg)
        if auto_gen_key:
            password = SystemUser.gen_password()
        return password

    @staticmethod
    def union_validate_public_key(public_key, attrs):
        username = attrs.get("username", "manual")
        protocol = attrs.get("protocol")
        password = attrs.get("password")
        private_key = attrs.get("private_key", None)
        auto_gen_key = attrs.get("auto_generate_key", False)

        if auto_gen_key and protocol == SystemUser.PROTOCOL_SSH:
            private_key, public_key = SystemUser.gen_key(username)
            attrs["private_key"] = private_key
        elif private_key:
            public_key = ssh_pubkey_gen(
                private_key, password=password, username=username
            )
        return public_key

    def validate(self, attrs):
        attrs = super().validate(attrs)
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



