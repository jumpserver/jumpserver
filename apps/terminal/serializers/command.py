# ~*~ coding: utf-8 ~*~
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from rest_framework import serializers

from common.utils import pretty_string, is_uuid, reverse, get_logger
from common.serializers.fields import LabeledChoiceField
from terminal.models import Command, Session
from terminal.const import RiskLevelChoices
from acls.models import CommandFilterACL, CommandGroup

logger = get_logger(__name__)
__all__ = ['SessionCommandSerializer', 'InsecureCommandAlertSerializer']


class SimpleSessionCommandSerializer(serializers.ModelSerializer):

    """ 简单Session命令序列类, 用来提取公共字段 """
    user = serializers.CharField(label=_("User"))  # 限制 64 字符，见 validate_user
    asset = serializers.CharField(max_length=128, label=_("Asset"))
    input = serializers.CharField(max_length=2048, label=_("Command"))
    session = serializers.CharField(max_length=36, label=_("Session ID"))
    risk_level = LabeledChoiceField(
        choices=RiskLevelChoices.choices,
        required=False, label=_("Risk level"),
    )
    org_id = serializers.CharField(
        max_length=36, required=False, default='', allow_null=True, allow_blank=True
    )

    class Meta:
        # 继承 ModelSerializer 解决 swagger risk_level type 为 object 的问题
        model = Command
        fields = ['user', 'asset', 'input', 'session', 'risk_level', 'org_id']

    def validate_user(self, value):
        if len(value) > 64:
            value = value[:32] + value[-32:]
        return value


class InsecureCommandAlertListSerializer(serializers.ListSerializer):
    msg_context_mapper: dict = {}

    def init_msg_context_mapper(self, attrs):
        attr_set = {
            (i.get('cmd_filter_acl', ''), i.get('cmd_group', ''),
             i.get('session', ''), i.get('input', ''))
            for i in attrs
        }

        acls = CommandFilterACL.objects \
            .filter(id__in=[i[0] for i in attr_set]) \
            .only('id', 'name')
        acl_mapper = {str(i.id): i for i in acls}

        acl_groups = CommandGroup.objects \
            .filter(id__in=[i[1] for i in attr_set]) \
            .only('id', 'name')
        acl_group_mapper = {str(i.id): i for i in acl_groups}

        sessions = Session.objects \
            .filter(id__in=[i[2] for i in attr_set]) \
            .only('id', 'org_id', 'asset', 'asset_id', 'user',
                  'user_id', 'account', 'account_id')
        session_mapper = {str(i.id): i for i in sessions}

        mapper = dict()
        for acl_id, acl_group_id, session_id, command in attr_set:
            acl = acl_mapper.get(acl_id)
            if not acl:
                logger.info(f'ACL not found: {acl_id}')
            acl_group = acl_group_mapper.get(acl_group_id)
            if not acl_group:
                logger.info(f'ACL group not found: {acl_group_id}')
            session = session_mapper.get(session_id)
            if not session:
                logger.info(f'Session not found: {session_id}')
            _ = {
                'user': {
                    'id': session.user_id,
                    'name': session.user,
                    'label': 'User',
                    'url': reverse(
                        'users:user-detail', kwargs={'pk': session.user_id},
                        api_to_ui=True, external=True, is_console=True
                    ) + '?oid={}'.format(session.org_id),
                },
                'asset': {
                    'id': session.asset_id,
                    'name': session.asset,
                    'label': 'Asset',
                    'url': reverse(
                        'assets:asset-detail', kwargs={'pk': session.asset_id},
                        api_to_ui=True, external=True, is_console=True
                    ) + '?oid={}'.format(session.org_id),
                },
                'account': {
                    'id': session.account_id,
                    'name': session.account,
                    'label': 'Account',
                    'url': reverse(
                        'accounts:account-detail', kwargs={'pk': session.account_id},
                        api_to_ui=True, external=True, is_console=True
                    ) + '?oid={}'.format(session.org_id),
                },
                'command': {
                    'id': '',
                    'name': command,
                    'label': 'Command',
                    'url': '',
                },
                'acl': {
                    'id': acl.id,
                    'name': acl.name,
                    'label': 'Command acl',
                    'instance': acl,
                    'url': settings.SITE_URL + f'/ui/#/console/perms/cmd-acls/{acl.id}/',
                },
                'acl_group': {
                    'id': acl_group.id,
                    'name': acl_group.name,
                    'label': 'Command acl group',
                    'url': settings.SITE_URL + f'/ui/#/console/perms/cmd-groups/{acl_group.id}/',
                },
                'session': {
                    'id': str(session.id),
                    'name': '',
                    'label': 'Session',
                    'url': reverse(
                        'api-terminal:session-detail', kwargs={'pk': session.id},
                        external=True, api_to_ui=True
                    ) + '?oid={}'.format(session.org_id)
                        .replace('/terminal/sessions/', '/audit/sessions/sessions/'),
                },
                'org': {
                    'id': session.org_id,
                    'name': session.org_id,
                    'label': 'Organization',
                    'url': '',
                },
            }
            mapper[session_id] = _
        self.msg_context_mapper = mapper

    def to_representation(self, data):
        datas = super().to_representation(data)
        self.init_msg_context_mapper(datas)
        for data in datas:
            session_id = data.get('session')
            context = self.msg_context_mapper.get(session_id)
            data['msg_context'] = context
        return datas


class InsecureCommandAlertSerializer(SimpleSessionCommandSerializer):
    cmd_filter_acl = serializers.CharField(
        max_length=36, required=False, label=_("Command Filter ACL")
    )
    cmd_group = serializers.CharField(
        max_length=36, required=True, label=_("Command Group")
    )

    class Meta(SimpleSessionCommandSerializer.Meta):
        list_serializer_class = InsecureCommandAlertListSerializer
        fields = SimpleSessionCommandSerializer.Meta.fields + [
            'cmd_filter_acl', 'cmd_group',
        ]

    def validate(self, attrs):
        if not is_uuid(attrs['cmd_filter_acl']):
            raise serializers.ValidationError(
                _("Invalid command filter ACL id")
            )
        if not is_uuid(attrs['cmd_group']):
            raise serializers.ValidationError(
                _("Invalid command group id")
            )
        if not is_uuid(attrs['session']):
            raise serializers.ValidationError(
                _("Invalid session id")
            )
        return super().validate(attrs)


class SessionCommandSerializerMixin(serializers.Serializer):
    """使用这个类作为基础Command Log Serializer类, 用来序列化"""
    id = serializers.UUIDField(read_only=True)
    # 限制 64 字符，不能直接迁移成 128 字符，命令表数据量会比较大
    account = serializers.CharField(label=_("Account "))
    output = serializers.CharField(max_length=2048, allow_blank=True, label=_("Output"))
    timestamp = serializers.IntegerField(label=_('Timestamp'))
    timestamp_display = serializers.DateTimeField(read_only=True, label=_('Datetime'))
    remote_addr = serializers.CharField(read_only=True, label=_('Remote Address'))

    def validate_account(self, value):
        if len(value) > 64:
            value = pretty_string(value, 64)
        return value


class SessionCommandSerializer(SessionCommandSerializerMixin, SimpleSessionCommandSerializer):
    """ 字段排序序列类 """

    class Meta(SimpleSessionCommandSerializer.Meta):
        fields = SimpleSessionCommandSerializer.Meta.fields + [
            'id', 'account', 'output', 'timestamp', 'timestamp_display', 'remote_addr'
        ]
