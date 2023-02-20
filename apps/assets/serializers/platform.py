from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from assets.const.web import FillType
from common.serializers import WritableNestedModelSerializer
from common.serializers.fields import LabeledChoiceField
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
    autofill = serializers.ChoiceField(default='basic', choices=FillType.choices, label=_("Autofill"))
    username_selector = serializers.CharField(
        default="", allow_blank=True, label=_("Username selector")
    )
    password_selector = serializers.CharField(
        default="", allow_blank=True, label=_("Password selector")
    )
    submit_selector = serializers.CharField(
        default="", allow_blank=True, label=_("Submit selector")
    )
    script = serializers.JSONField(default=list, label=_("Script"))

    # Redis
    auth_username = serializers.BooleanField(default=False, label=_("Auth with username"))


class PlatformAutomationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformAutomation
        fields = [
            "id",
            "ansible_enabled", "ansible_config",
            "ping_enabled", "ping_method",
            "push_account_enabled", "push_account_method",
            "gather_facts_enabled", "gather_facts_method",
            "change_secret_enabled", "change_secret_method",
            "verify_account_enabled", "verify_account_method",
            "gather_accounts_enabled", "gather_accounts_method",
        ]
        extra_kwargs = {
            # 启用资产探测
            "ping_enabled": {"label": _("Ping enabled")},
            "ping_method": {"label": _("Ping method")},
            "gather_facts_enabled": {"label": _("Gather facts enabled")},
            "gather_facts_method": {"label": _("Gather facts method")},
            "verify_account_enabled": {"label": _("Verify account enabled")},
            "verify_account_method": {"label": _("Verify account method")},
            "change_secret_enabled": {"label": _("Change secret enabled")},
            "change_secret_method": {"label": _("Change secret method")},
            "push_account_enabled": {"label": _("Push account enabled")},
            "push_account_method": {"label": _("Push account method")},
            "gather_accounts_enabled": {"label": _("Gather accounts enabled")},
            "gather_accounts_method": {"label": _("Gather accounts method")},
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
        label=_("Su method"), required=False, default="sudo", allow_null=True
    )

    class Meta:
        model = Platform
        fields_mini = ["id", "name", "internal"]
        fields_small = fields_mini + [
            "category", "type", "charset",
        ]
        fields_other = [
            'date_created', 'date_updated', 'created_by', 'updated_by',
        ]
        fields = fields_small + [
            "protocols", "domain_enabled", "su_enabled",
            "su_method", "automation", "comment",
        ] + fields_other
        extra_kwargs = {
            "su_enabled": {"label": _('Su enabled')},
            "domain_enabled": {"label": _('Domain enabled')},
            "domain_default": {"label": _('Default Domain')},
        }

    @classmethod
    def setup_eager_loading(cls, queryset):
        queryset = queryset.prefetch_related(
            'protocols', 'automation'
        )
        return queryset


class PlatformOpsMethodSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=50, label=_("Name"))
    category = serializers.CharField(max_length=50, label=_("Category"))
    type = serializers.ListSerializer(child=serializers.CharField())
    method = serializers.CharField()
