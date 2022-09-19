from rest_framework import serializers
from django.utils.translation import gettext_lazy as _

from common.drf.fields import LabeledChoiceField
from common.drf.serializers import JMSWritableNestedModelSerializer
from ..models import Platform, PlatformProtocol, PlatformAutomation
from ..const import Category, AllTypes


__all__ = ['PlatformSerializer', 'PlatformOpsMethodSerializer']


class ProtocolSettingSerializer(serializers.Serializer):
    SECURITY_CHOICES = [
        ('any', 'Any'),
        ('rdp', 'RDP'),
        ('tls', 'TLS'),
        ('nla', 'NLA'),
    ]
    # RDP
    console = serializers.BooleanField(required=False)
    security = serializers.ChoiceField(choices=SECURITY_CHOICES, default='any')

    # SFTP
    sftp_enabled = serializers.BooleanField(default=True, label=_("SFTP enabled"))
    sftp_home = serializers.CharField(default='/tmp', label=_("SFTP home"))


class PlatformAutomationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformAutomation
        fields = [
            'id', 'ping_enabled', 'ping_method',
            'gather_facts_enabled', 'gather_facts_method',
            'create_account_enabled', 'create_account_method',
            'change_password_enabled', 'change_password_method',
            'verify_account_enabled', 'verify_account_method',
            'gather_accounts_enabled', 'gather_accounts_method',
        ]
        extra_kwargs = {
            'ping_enabled': {'label': '启用资产探测'},
            'ping_method': {'label': '探测方式'},
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


class PlatformProtocolsSerializer(serializers.ModelSerializer):
    setting = ProtocolSettingSerializer(required=False, allow_null=True)

    class Meta:
        model = PlatformProtocol
        fields = ['id', 'name', 'port', 'setting']


class PlatformSerializer(JMSWritableNestedModelSerializer):
    type = LabeledChoiceField(choices=AllTypes.choices, label=_("Type"))
    category = LabeledChoiceField(choices=Category.choices, label=_("Category"))
    protocols = PlatformProtocolsSerializer(label=_('Protocols'), many=True, required=False)
    automation = PlatformAutomationSerializer(label=_('Automation'), required=False)
    su_method = LabeledChoiceField(
        choices=[('sudo', 'sudo su -'), ('su', 'su - ')],
        label='切换方式', required=False, default='sudo'
    )
    brand = LabeledChoiceField(choices=[], label='厂商', required=False, allow_null=True)

    class Meta:
        model = Platform
        fields_mini = ['id', 'name', 'internal']
        fields_small = fields_mini + [
            'category', 'type', 'charset',
        ]
        fields = fields_small + [
            'protocols_enabled', 'protocols', 'domain_enabled',
            'su_enabled', 'su_method', 'brand', 'automation', 'comment',
        ]
        extra_kwargs = {
            'su_enabled': {'label': '启用切换账号'},
            'protocols_enabled': {'label': '启用协议'},
            'domain_enabled': {'label': "启用网域"},
            'domain_default': {'label': "默认网域"},
        }


class PlatformOpsMethodSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=50, label=_('Name'))
    category = serializers.CharField(max_length=50, label=_('Category'))
    type = serializers.ListSerializer(child=serializers.CharField())
    method = serializers.CharField()
