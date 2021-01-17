from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from django.db.models import Count

from common.drf.serializers import AdaptedBulkListSerializer
from common.mixins.serializers import BulkSerializerMixin
from common.utils import ssh_pubkey_gen
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import SystemUser, Asset
from .base import AuthSerializerMixin

__all__ = [
    'SystemUserSerializer', 'SystemUserListSerializer',
    'SystemUserSimpleSerializer', 'SystemUserAssetRelationSerializer',
    'SystemUserNodeRelationSerializer', 'SystemUserTaskSerializer',
    'SystemUserUserRelationSerializer', 'SystemUserWithAuthInfoSerializer',
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
            'id', 'name', 'username', 'protocol',
            'password', 'public_key', 'private_key',
            'login_mode', 'login_mode_display',
            'priority', 'username_same_with_user',
            'auto_push', 'cmd_filters', 'sudo', 'shell', 'comment',
            'auto_generate_key', 'sftp_root', 'token',
            'assets_amount', 'date_created', 'created_by',
            'home', 'system_groups', 'ad_domain'
        ]
        extra_kwargs = {
            'password': {"write_only": True},
            'public_key': {"write_only": True},
            'private_key': {"write_only": True},
            'token': {"write_only": True},
            'nodes_amount': {'label': _('Nodes amount')},
            'assets_amount': {'label': _('Assets amount')},
            'login_mode_display': {'label': _('Login mode display')},
            'created_by': {'read_only': True},
            'ad_domain': {'required': False, 'allow_blank': True, 'label': _('Ad domain')},
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

    def validate_username_same_with_user(self, username_same_with_user):
        if not username_same_with_user:
            return username_same_with_user
        protocol = self.initial_data.get("protocol", "ssh")
        queryset = SystemUser.objects.filter(
                protocol=protocol, username_same_with_user=True
        )
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        exists = queryset.exists()
        if not exists:
            return username_same_with_user
        error = _("Username same with user with protocol {} only allow 1").format(protocol)
        raise serializers.ValidationError(error)

    def validate_username(self, username):
        if username:
            return username
        login_mode = self.initial_data.get("login_mode")
        protocol = self.initial_data.get("protocol")
        username_same_with_user = self.initial_data.get("username_same_with_user")
        if username_same_with_user:
            return ''
        if login_mode == SystemUser.LOGIN_AUTO and \
                protocol != SystemUser.PROTOCOL_VNC:
            msg = _('* Automatic login mode must fill in the username.')
            raise serializers.ValidationError(msg)
        return username

    def validate_sftp_root(self, value):
        if value in ['home', 'tmp']:
            return value
        if not value.startswith('/'):
            error = _("Path should starts with /")
            raise serializers.ValidationError(error)
        return value

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
        auto_gen_key = attrs.pop("auto_generate_key", False)
        protocol = attrs.get("protocol")

        if protocol not in [SystemUser.PROTOCOL_RDP, SystemUser.PROTOCOL_SSH]:
            return attrs

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
        return attrs


class SystemUserListSerializer(SystemUserSerializer):

    class Meta(SystemUserSerializer.Meta):
        fields = [
            'id', 'name', 'username', 'protocol',
            'password', 'public_key', 'private_key',
            'login_mode', 'login_mode_display',
            'priority', "username_same_with_user",
            'auto_push', 'sudo', 'shell', 'comment',
            "assets_amount", 'home', 'system_groups',
            'auto_generate_key', 'ad_domain',
            'sftp_root',
        ]
        extra_kwargs = {
            'password': {"write_only": True},
            'public_key': {"write_only": True},
            'private_key': {"write_only": True},
            'nodes_amount': {'label': _('Nodes amount')},
            'assets_amount': {'label': _('Assets amount')},
            'login_mode_display': {'label': _('Login mode display')},
            'created_by': {'read_only': True},
            'ad_domain': {'label': _('Ad domain')},
        }

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.annotate(assets_amount=Count("assets"))
        return queryset


class SystemUserWithAuthInfoSerializer(SystemUserSerializer):
    class Meta(SystemUserSerializer.Meta):
        fields = [
            'id', 'name', 'username', 'protocol',
            'password', 'public_key', 'private_key',
            'login_mode', 'login_mode_display',
            'priority', 'username_same_with_user',
            'auto_push', 'sudo', 'shell', 'comment',
            'auto_generate_key', 'sftp_root', 'token',
            'ad_domain',
        ]
        extra_kwargs = {
            'nodes_amount': {'label': _('Node')},
            'assets_amount': {'label': _('Asset')},
            'login_mode_display': {'label': _('Login mode display')},
            'created_by': {'read_only': True},
        }


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

    def get_node_display(self, obj):
        return obj.node.full_value


class SystemUserUserRelationSerializer(RelationMixin, serializers.ModelSerializer):
    user_display = serializers.ReadOnlyField()

    class Meta(RelationMixin.Meta):
        model = SystemUser.users.through
        fields = [
            'id', "user", "user_display",
        ]


class SystemUserTaskSerializer(serializers.Serializer):
    ACTION_CHOICES = (
        ("test", "test"),
        ("push", "push"),
    )
    action = serializers.ChoiceField(choices=ACTION_CHOICES, write_only=True)
    asset = serializers.PrimaryKeyRelatedField(
        queryset=Asset.objects, allow_null=True, required=False, write_only=True
    )
    assets = serializers.PrimaryKeyRelatedField(
        queryset=Asset.objects, allow_null=True, required=False, write_only=True,
        many=True
    )
    task = serializers.CharField(read_only=True)
