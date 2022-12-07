from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from common.drf.fields import LabeledChoiceField
from common.drf.serializers import WritableNestedModelSerializer
from ..const import Category, AllTypes
from ..models import Platform, PlatformProtocol, PlatformAutomation

__all__ = ["PlatformSerializer", "PlatformOpsMethodSerializer"]


class ProtocolSettingSerializer(serializers.Serializer):
    SECURITY_CHOICES = [
        ("any", "Any"),
        ("rdp", "RDP"),
        ("tls", "TLS"),
        ("nla", "NLA"),
    ]
    # RDP
    console = serializers.BooleanField(required=False)
    security = serializers.ChoiceField(choices=SECURITY_CHOICES, default="any")

    # SFTP
    sftp_enabled = serializers.BooleanField(default=True, label=_("SFTP enabled"))
    sftp_home = serializers.CharField(default="/tmp", label=_("SFTP home"))

    # HTTP
    autofile = serializers.BooleanField(default=False, label=_("Autofill"))
    username_selector = serializers.CharField(
        default="", allow_blank=True, label=_("Username selector")
    )
    password_selector = serializers.CharField(
        default="", allow_blank=True, label=_("Password selector")
    )
    submit_selector = serializers.CharField(
        default="", allow_blank=True, label=_("Submit selector")
    )


class PlatformAutomationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformAutomation
        fields = [
            "id",
            "ansible_enabled", "ansible_config",
            "ping_enabled", "ping_method",
            "gather_facts_enabled", "gather_facts_method",
            "push_account_enabled", "push_account_method",
            "change_secret_enabled", "change_secret_method",
            "verify_account_enabled", "verify_account_method",
            "gather_accounts_enabled", "gather_accounts_method",
        ]
        extra_kwargs = {
            "ping_enabled": {"label": "启用资产探测"},
            "ping_method": {"label": "探测方式"},
            "gather_facts_enabled": {"label": "启用收集信息"},
            "gather_facts_method": {"label": "收集信息方式"},
            "verify_account_enabled": {"label": "启用校验账号"},
            "verify_account_method": {"label": "校验账号方式"},
            "push_account_enabled": {"label": "启用推送账号"},
            "push_account_method": {"label": "推送账号方式"},
            "change_secret_enabled": {"label": "启用账号改密"},
            "change_secret_method": {"label": "账号创建改密方式"},
            "gather_accounts_enabled": {"label": "启用账号收集"},
            "gather_accounts_method": {"label": "收集账号方式"},
        }


class PlatformProtocolsSerializer(serializers.ModelSerializer):
    setting = ProtocolSettingSerializer(required=False, allow_null=True)
    primary = serializers.BooleanField(read_only=True, label=_("Primary"))

    class Meta:
        model = PlatformProtocol
        fields = [
            "id", "name", "port", "primary",
            "default", "required", "secret_types",
            "setting",
        ]


class PlatformSerializer(WritableNestedModelSerializer):
    charset = LabeledChoiceField(
        choices=Platform.CharsetChoices.choices, label=_("Charset")
    )
    type = LabeledChoiceField(choices=AllTypes.choices(), label=_("Type"))
    category = LabeledChoiceField(choices=Category.choices, label=_("Category"))
    protocols = PlatformProtocolsSerializer(
        label=_("Protocols"), many=True, required=False
    )
    automation = PlatformAutomationSerializer(label=_("Automation"), required=False)
    su_method = LabeledChoiceField(
        choices=[("sudo", "sudo su -"), ("su", "su - ")],
        label="切换方式",
        required=False,
        default="sudo",
    )

    class Meta:
        model = Platform
        fields_mini = ["id", "name", "internal"]
        fields_small = fields_mini + [
            "category", "type", "charset",
        ]
        fields = fields_small + [
            "protocols_enabled", "protocols",
            "domain_enabled", "su_enabled",
            "su_method", "automation",
            "comment",
        ]
        extra_kwargs = {
            "su_enabled": {"label": "启用切换账号"},
            "protocols_enabled": {"label": "启用协议"},
            "domain_enabled": {"label": "启用网域"},
            "domain_default": {"label": "默认网域"},
        }


class PlatformOpsMethodSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=50, label=_("Name"))
    category = serializers.CharField(max_length=50, label=_("Category"))
    type = serializers.ListSerializer(child=serializers.CharField())
    method = serializers.CharField()
