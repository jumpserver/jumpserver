from rest_framework import serializers

from django.utils.translation import ugettext_lazy as _

from common.serializers import AdaptedBulkListSerializer
from orgs.mixins import BulkOrgResourceModelSerializer
from ..models import SystemUser
from .base import AuthSerializer, AuthSerializerMixin


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
        if not self.instance and not auto_gen_key and not password and not private_key:
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



