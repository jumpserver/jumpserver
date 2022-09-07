from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from common.drf.fields import LabeledChoiceField
from common.drf.serializers import JMSWritableNestedModelSerializer
from ..models import Platform, PlatformProtocol
from ..const import Category, AllTypes


__all__ = ['PlatformSerializer', 'PlatformOpsMethodSerializer']


class ProtocolSettingSerializer(serializers.Serializer):
    SECURITY_CHOICES = [
        ('any', 'Any'),
        ('rdp', 'RDP'),
        ('tls', 'TLS'),
        ('nla', 'NLA'),
    ]
    # Common
    required = serializers.BooleanField(required=True, initial=False, label=_("Required"))

    # RDP
    console = serializers.BooleanField(required=False)
    security = serializers.ChoiceField(choices=SECURITY_CHOICES, default='any', required=False)
    # SFTP
    sftp_home = serializers.CharField(default='/tmp', required=False)


class PlatformProtocolsSerializer(serializers.ModelSerializer):
    setting = ProtocolSettingSerializer(required=False, allow_null=True)

    class Meta:
        model = PlatformProtocol
        fields = ['id', 'name', 'port', 'setting']


class PlatformSerializer(JMSWritableNestedModelSerializer):
    type = LabeledChoiceField(choices=AllTypes.choices, label=_("Type"))
    category = LabeledChoiceField(choices=Category.choices, label=_("Category"))
    protocols = PlatformProtocolsSerializer(label=_('Protocols'), many=True, required=False)
    type_constraints = serializers.ReadOnlyField(required=False, read_only=True)
    su_method = LabeledChoiceField(
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
            'protocols_enabled', 'protocols',
            'gather_facts_enabled', 'gather_facts_method',
            'su_enabled', 'su_method',
            'gather_accounts_enabled', 'gather_accounts_method',
            'create_account_enabled', 'create_account_method',
            'verify_account_enabled', 'verify_account_method',
            'change_password_enabled', 'change_password_method',
            'type_constraints', 'comment', 'charset',
        ]
        extra_kwargs = {
            'su_enabled': {'label': '启用切换账号'},
            'domain_enabled': {'label': "启用网域"},
            'domain_default': {'label': "默认网域"},
            'gather_facts_enabled': {'label': '启用收集信息'},
            'gather_facts_method': {'label': '收集信息方式'},
            'verify_account_enabled': {'label': '启用校验账号'},
            'verify_account_method': {'label': '校验账号方式'},
            'create_account_enabled': {'label': '启用创建账号'},
            'create_account_method': {'label': '创建账号方式'},
            'change_password_enabled': {'label': '启用账号创建改密'},
            'change_password_method': {'label': '账号创建改密方式'},
            'gather_accounts_enabled': {'label': '启用账号收集'},
            'gather_accounts_method': {'label': '收集账号方式'},
        }

    def validate(self, attrs):
        fields_to_check = [
            ('verify_account_enabled', 'verify_account_method'),
            ('create_account_enabled', 'create_account_method'),
            ('change_password_enabled', 'change_password_method'),
        ]
        for method_enabled, method_name in fields_to_check:
            if attrs.get(method_enabled, False) and not attrs.get(method_name, False):
                raise serializers.ValidationError({method_name: _('This field is required.')})
        return attrs


class PlatformOpsMethodSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=50, label=_('Name'))
    category = serializers.CharField(max_length=50, label=_('Category'))
    type = serializers.ListSerializer(child=serializers.CharField())
    method = serializers.CharField()
