from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from common.validators import alphanumeric_re, alphanumeric_cn_re, alphanumeric_win_re
from orgs.mixins.serializers import BulkOrgResourceModelSerializer

__all__ = [
    'SystemUserSerializer', 'MiniSystemUserSerializer',
    'SystemUserSimpleSerializer',
]


class SystemUserSerializer(BulkOrgResourceModelSerializer):
    """
    系统用户
    """

    class Meta:
        model = SystemUser
        fields_mini = ['id', 'name', 'username', 'protocol']
        fields_small = fields_mini + [
            'login_mode', 'su_enabled', 'su_from',
            'date_created', 'date_updated', 'comment',
            'created_by',
        ]
        fields = fields_small
        extra_kwargs = {
            'cmd_filters': {"required": False, 'label': _('Command filter')},
            'login_mode_display': {'label': _('Login mode display')},
            'created_by': {'read_only': True},
            'ad_domain': {'required': False, 'allow_blank': True, 'label': _('Ad domain')},
            'su_from': {'help_text': _('Only ssh and automatic login system users are supported')}
        }

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
        protocol = self.get_initial_value("protocol")
        if username:
            if protocol == Protocol.telnet:
                regx = alphanumeric_cn_re
            elif protocol == Protocol.rdp:
                regx = alphanumeric_win_re
            else:
                regx = alphanumeric_re
            if not regx.match(username):
                raise serializers.ValidationError(_('Special char not allowed'))
            return username

        username_same_with_user = self.get_initial_value("username_same_with_user")
        if username_same_with_user:
            return ''

        login_mode = self.get_initial_value("login_mode")
        if login_mode == SystemUser.LOGIN_AUTO and protocol != Protocol.vnc \
                and protocol != Protocol.redis:
            msg = _('* Automatic login mode must fill in the username.')
            raise serializers.ValidationError(msg)
        return username

    @staticmethod
    def validate_sftp_root(value):
        if value in ['home', 'tmp']:
            return value
        if not value.startswith('/'):
            error = _("Path should starts with /")
            raise serializers.ValidationError(error)
        return value

    def validate_su_from(self, su_from: SystemUser):
        # self: su enabled
        su_enabled = self.get_initial_value('su_enabled', default=False)
        if not su_enabled:
            return
        if not su_from:
            error = _('This field is required.')
            raise serializers.ValidationError(error)
        # self: protocol ssh
        protocol = self.get_initial_value('protocol', default=Protocol.ssh.value)
        if protocol not in [Protocol.ssh.value]:
            error = _('Only ssh protocol system users are allowed')
            raise serializers.ValidationError(error)
        # su_from: protocol same
        if su_from.protocol != protocol:
            error = _('The protocol must be consistent with the current user: {}').format(protocol)
            raise serializers.ValidationError(error)
        # su_from: login model auto
        if su_from.login_mode != su_from.LOGIN_AUTO:
            error = _('Only system users with automatic login are allowed')
            raise serializers.ValidationError(error)
        return su_from


class MiniSystemUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemUser
        fields = SystemUserSerializer.Meta.fields_mini


class SystemUserSimpleSerializer(serializers.ModelSerializer):
    """
    系统用户最基本信息的数据结构
    """

    class Meta:
        model = SystemUser
        fields = ('id', 'name', 'username')


class SystemUserTempAuthSerializer(SystemUserSerializer):
    instance_id = serializers.CharField()

    class Meta(SystemUserSerializer.Meta):
        fields = ['instance_id', 'username', 'password']
