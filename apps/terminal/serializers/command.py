# ~*~ coding: utf-8 ~*~
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.serializers.fields import LabeledChoiceField
from common.utils import pretty_string, is_uuid, get_logger
from terminal.const import RiskLevelChoices
from terminal.models import Command

logger = get_logger(__name__)
__all__ = ['SessionCommandSerializer', 'InsecureCommandAlertSerializer']


class SimpleSessionCommandSerializer(serializers.ModelSerializer):
    """ 简单Session命令序列类, 用来提取公共字段 """
    user = serializers.CharField(label=_("User"))  # 限制 64 字符，见 validate_user
    asset = serializers.CharField(max_length=128, label=_("Asset"))
    input = serializers.CharField(label=_("Command"))
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


class InsecureCommandAlertSerializer(SimpleSessionCommandSerializer):
    cmd_filter_acl = serializers.CharField(
        max_length=36, required=False, label=_("Command Filter ACL")
    )
    cmd_group = serializers.CharField(
        max_length=36, required=True, label=_("Command Group")
    )

    class Meta(SimpleSessionCommandSerializer.Meta):
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
