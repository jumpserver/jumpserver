from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _
from django.db.models import Count

from common.mixins.serializers import BulkSerializerMixin
from common.utils import ssh_pubkey_gen
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import SystemUser, Asset
from .base import AuthSerializerMixin

__all__ = [
    'SystemUserSerializer',
    'SystemUserSimpleSerializer', 'SystemUserAssetRelationSerializer',
    'SystemUserNodeRelationSerializer', 'SystemUserTaskSerializer',
    'SystemUserUserRelationSerializer', 'SystemUserWithAuthInfoSerializer',
    'SystemUserTempAuthSerializer',
]


class SystemUserSerializer(AuthSerializerMixin, BulkOrgResourceModelSerializer):
    """
    系统用户
    """
    auto_generate_key = serializers.BooleanField(initial=True, required=False, write_only=True)
    type_display = serializers.ReadOnlyField(source='get_type_display', label=_('Type display'))
    ssh_key_fingerprint = serializers.ReadOnlyField(label=_('SSH key fingerprint'))

    class Meta:
        model = SystemUser
        fields_mini = ['id', 'name', 'username']
        fields_write_only = ['password', 'public_key', 'private_key']
        fields_small = fields_mini + fields_write_only + [
            'type', 'type_display', 'protocol', 'login_mode', 'login_mode_display',
            'priority', 'sudo', 'shell', 'sftp_root', 'token', 'ssh_key_fingerprint',
            'home', 'system_groups', 'ad_domain',
            'username_same_with_user', 'auto_push', 'auto_generate_key',
            'date_created', 'date_updated',
            'comment', 'created_by',
        ]
        fields_m2m = ['cmd_filters', 'assets_amount']
        fields = fields_small + fields_m2m
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
        login_mode = self.get_initial_value("login_mode")
        protocol = self.get_initial_value("protocol")

        if login_mode == SystemUser.LOGIN_MANUAL:
            value = False
        elif protocol not in SystemUser.SUPPORT_PUSH_PROTOCOLS:
            value = False
        return value

    def validate_auto_generate_key(self, value):
        login_mode = self.get_initial_value("login_mode")
        protocol = self.get_initial_value("protocol")

        if self.context["request"].method.lower() != "post":
            value = False
        elif self.instance:
            value = False
        elif login_mode == SystemUser.LOGIN_MANUAL:
            value = False
        elif protocol not in SystemUser.SUPPORT_PUSH_PROTOCOLS:
            value = False
        return value

    def validate_username_same_with_user(self, username_same_with_user):
        if not username_same_with_user:
            return username_same_with_user
        protocol = self.get_initial_value("protocol", "ssh")
        queryset = SystemUser.objects.filter(
            protocol=protocol,
            username_same_with_user=True
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
        login_mode = self.get_initial_value("login_mode")
        protocol = self.get_initial_value("protocol")
        username_same_with_user = self.get_initial_value("username_same_with_user")

        if username_same_with_user:
            return ''

        if login_mode == SystemUser.LOGIN_AUTO and protocol != SystemUser.Protocol.vnc:
            msg = _('* Automatic login mode must fill in the username.')
            raise serializers.ValidationError(msg)
        return username

    def validate_home(self, home):
        username_same_with_user = self.get_initial_value("username_same_with_user")
        if username_same_with_user:
            return ''
        return home

    def validate_sftp_root(self, value):
        if value in ['home', 'tmp']:
            return value
        if not value.startswith('/'):
            error = _("Path should starts with /")
            raise serializers.ValidationError(error)
        return value

    def validate_admin_user(self, attrs):
        if self.instance:
            tp = self.instance.type
        else:
            tp = attrs.get('type')
        if tp != SystemUser.Type.admin:
            return attrs
        attrs['protocol'] = SystemUser.Protocol.ssh
        attrs['login_mode'] = SystemUser.LOGIN_AUTO
        attrs['username_same_with_user'] = False
        attrs['auto_push'] = False
        return attrs

    def validate_password(self, password):
        super().validate_password(password)
        auto_gen_key = self.get_initial_value("auto_generate_key", False)
        private_key = self.get_initial_value("private_key")
        login_mode = self.get_initial_value("login_mode")

        if not self.instance and not auto_gen_key and not password and \
                not private_key and login_mode == SystemUser.LOGIN_AUTO:
            raise serializers.ValidationError(_("Password or private key required"))
        return password

    def validate_gen_key(self, attrs):
        username = attrs.get("username", "manual")
        auto_gen_key = attrs.pop("auto_generate_key", False)
        protocol = attrs.get("protocol")

        if protocol not in SystemUser.SUPPORT_PUSH_PROTOCOLS:
            return attrs

        # 自动生成
        if auto_gen_key and not self.instance:
            password = SystemUser.gen_password()
            attrs["password"] = password
            if protocol == SystemUser.Protocol.ssh:
                private_key, public_key = SystemUser.gen_key(username)
                attrs["private_key"] = private_key
                attrs["public_key"] = public_key
        # 如果设置了private key，没有设置public key则生成
        elif attrs.get("private_key", None):
            private_key = attrs["private_key"]
            password = attrs.get("password")
            public_key = ssh_pubkey_gen(private_key, password=password, username=username)
            attrs["public_key"] = public_key
        return attrs

    def validate(self, attrs):
        attrs = self.validate_admin_user(attrs)
        attrs = self.validate_gen_key(attrs)
        return attrs

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.annotate(assets_amount=Count("assets"))
        return queryset


class SystemUserWithAuthInfoSerializer(SystemUserSerializer):
    class Meta(SystemUserSerializer.Meta):
        fields_mini = ['id', 'name', 'username']
        fields_write_only = ['password', 'public_key', 'private_key']
        fields_small = fields_mini + fields_write_only + [
            'protocol', 'login_mode', 'login_mode_display', 'priority',
            'sudo', 'shell', 'ad_domain', 'sftp_root', 'token',
            "username_same_with_user", 'auto_push', 'auto_generate_key',
            'comment',
        ]
        fields = fields_small
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
    systemuser_display = serializers.ReadOnlyField(label=_("System user name"))
    org_name = serializers.ReadOnlyField(label=_("Org name"))

    def get_field_names(self, declared_fields, info):
        fields = super().get_field_names(declared_fields, info)
        fields.extend(['systemuser', "systemuser_display", "org_name"])
        return fields


class SystemUserAssetRelationSerializer(RelationMixin, serializers.ModelSerializer):
    asset_display = serializers.ReadOnlyField(label=_('Asset hostname'))

    class Meta:
        model = SystemUser.assets.through
        fields = [
            "id", "asset", "asset_display", 'systemuser', 'systemuser_display',
            "connectivity", 'date_verified', 'org_id'
        ]
        use_model_bulk_create = True
        model_bulk_create_kwargs = {
            'ignore_conflicts': True
        }


class SystemUserNodeRelationSerializer(RelationMixin, serializers.ModelSerializer):
    node_display = serializers.SerializerMethodField()

    class Meta:
        model = SystemUser.nodes.through
        fields = [
            'id', 'node', "node_display",
        ]

    def get_node_display(self, obj):
        return obj.node.full_value


class SystemUserUserRelationSerializer(RelationMixin, serializers.ModelSerializer):
    user_display = serializers.ReadOnlyField()

    class Meta:
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


class SystemUserTempAuthSerializer(SystemUserSerializer):
    instance_id = serializers.CharField()

    class Meta(SystemUserSerializer.Meta):
        fields = ['instance_id', 'username', 'password']
