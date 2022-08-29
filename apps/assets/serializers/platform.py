from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from common.drf.fields import ChoiceDisplayField
from common.drf.serializers import JMSWritableNestedModelSerializer
from ..models import Platform, PlatformProtocol
from ..const import Category, AllTypes


__all__ = ['PlatformSerializer']


class ProtocolSettingSerializer(serializers.Serializer):
    SECURITY_CHOICES = [
        ('any', 'Any'),
        ('rdp', 'RDP'),
        ('tls', 'TLS'),
        ('nla', 'NLA'),
    ]
    console = serializers.BooleanField(required=False)
    security = serializers.ChoiceField(choices=SECURITY_CHOICES, default='any', required=False)


class PlatformProtocolsSerializer(serializers.ModelSerializer):
    setting = ProtocolSettingSerializer(required=False)

    class Meta:
        model = PlatformProtocol
        fields = ['id', 'name', 'port', 'setting']


class PlatformSerializer(JMSWritableNestedModelSerializer):
    type = ChoiceDisplayField(choices=AllTypes.choices, label=_("Type"))
    category = ChoiceDisplayField(choices=Category.choices, label=_("Category"))
    protocols = PlatformProtocolsSerializer(label=_('Protocols'), many=True, required=False)
    type_constraints = serializers.ReadOnlyField(required=False, read_only=True)
    su_method = ChoiceDisplayField(
        choices=[('sudo', 'sudo su -'), ('su', 'su - ')],
        label='切换方式', required=False, default='sudo'
    )

    class Meta:
        model = Platform
        fields_mini = ['id', 'name', 'internal']
        fields_small = fields_mini + [
            'category', 'type',
        ]
        fields = fields_small + [
            'domain_enabled', 'domain_default', 'su_enabled', 'su_method',
            'protocols_enabled', 'protocols', 'ping_enabled', 'ping_method',
            'verify_account_enabled', 'verify_account_method',
            'create_account_enabled', 'create_account_method',
            'change_password_enabled', 'change_password_method',
            'type_constraints', 'comment', 'charset',
        ]
        extra_kwargs = {
            'su_enabled': {'label': '启用切换账号'},
            'verify_account_enabled': {'label': '启用校验账号'},
            'verify_account_method': {'label': '校验账号方式'},
            'create_account_enabled': {'label': '启用创建账号'},
            'create_account_method': {'label': '创建账号方式'},
            'change_password_enabled': {'label': '启用账号改密'},
            'change_password_method': {'label': '账号改密方式'},
        }

    def validate_verify_account_method(self, value):
        if not value and self.initial_data.get('verify_account_enabled', False):
            raise serializers.ValidationError(_('This field is required.'))
        return value

    def validate_create_account_method(self, value):
        if not value and self.initial_data.get('create_account_enabled', False):
            raise serializers.ValidationError(_('This field is required.'))
        return value

    def validate_change_password_method(self, value):
        if not value and self.initial_data.get('change_password_enabled', False):
            raise serializers.ValidationError(_('This field is required.'))
        return value
