from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from common.serializers import (
    WritableNestedModelSerializer, type_field_map, MethodSerializer,
    DictSerializer, create_serializer_class, ResourceLabelsMixin
)
from common.serializers.fields import LabeledChoiceField
from common.utils import lazyproperty
from ..const import Category, AllTypes, Protocol
from ..models import Platform, PlatformProtocol, PlatformAutomation

__all__ = ["PlatformSerializer", "PlatformOpsMethodSerializer", "PlatformProtocolSerializer"]


class PlatformAutomationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlatformAutomation
        fields = [
            "id",
            "ansible_enabled", "ansible_config",
            "ping_enabled", "ping_method", "ping_params",
            "push_account_enabled", "push_account_method", "push_account_params",
            "gather_facts_enabled", "gather_facts_method", "gather_facts_params",
            "change_secret_enabled", "change_secret_method", "change_secret_params",
            "verify_account_enabled", "verify_account_method", "verify_account_params",
            "gather_accounts_enabled", "gather_accounts_method", "gather_accounts_params",
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


class PlatformProtocolSerializer(serializers.ModelSerializer):
    setting = MethodSerializer(required=False, label=_("Setting"))
    port_from_addr = serializers.BooleanField(label=_("Port from addr"), read_only=True)

    class Meta:
        model = PlatformProtocol
        fields = [
            "id", "name", "port", "port_from_addr",
            "primary", "required", "default", "public",
            "secret_types", "setting",
        ]
        extra_kwargs = {
            "primary": {
                "help_text": _(
                    "This protocol is primary, and it must be set when adding assets. "
                    "Additionally, there can only be one primary protocol."
                )
            },
            "required": {
                "help_text": _("This protocol is required, and it must be set when adding assets.")
            },
            "default": {
                "help_text": _("This protocol is default, when adding assets, it will be displayed by default.")
            },
            "public": {
                "help_text": _("This protocol is public, asset will show this protocol to user")
            },
        }

    def get_setting_serializer(self):
        request = self.context.get('request')
        default_field = DictSerializer(required=False)

        if not request:
            return default_field

        if self.instance and isinstance(self.instance, (QuerySet, list)):
            instance = self.instance[0]
        else:
            instance = self.instance

        protocol = request.query_params.get('name', '')
        if instance and not protocol:
            protocol = instance.name

        protocol_settings = Protocol.settings()
        setting_fields = protocol_settings.get(protocol, {}).get('setting')
        if not setting_fields:
            return default_field

        setting_fields = [{'name': k, **v} for k, v in setting_fields.items()]
        name = '{}ProtocolSettingSerializer'.format(protocol.capitalize())
        return create_serializer_class(name, setting_fields)()

    def validate(self, cleaned_data):
        name = cleaned_data.get('name')
        if name in ['winrm']:
            cleaned_data['public'] = False
        return cleaned_data

    def to_file_representation(self, data):
        return '{name}/{port}'.format(**data)

    def to_file_internal_value(self, data):
        name, port = data.split('/')
        return {'name': name, 'port': port}


class PlatformCustomField(serializers.Serializer):
    TYPE_CHOICES = [(t, t) for t, c in type_field_map.items()]
    name = serializers.CharField(label=_("Name"), max_length=128)
    label = serializers.CharField(label=_("Label"), max_length=128)
    type = serializers.ChoiceField(choices=TYPE_CHOICES, label=_("Type"), default='str')
    default = serializers.CharField(default="", allow_blank=True, label=_("Default"), max_length=1024)
    help_text = serializers.CharField(default="", allow_blank=True, label=_("Help text"), max_length=1024)
    choices = serializers.ListField(default=list, label=_("Choices"), required=False)


class PlatformSerializer(ResourceLabelsMixin, WritableNestedModelSerializer):
    SU_METHOD_CHOICES = [
        ("sudo", "sudo su -"),
        ("su", "su - "),
        ("enable", "enable"),
        ("super", "super 15"),
        ("super_level", "super level 15")
    ]
    id = serializers.IntegerField(
        label='ID', required=False,
        validators=[UniqueValidator(queryset=Platform.objects.all())]
    )
    charset = LabeledChoiceField(choices=Platform.CharsetChoices.choices, label=_("Charset"), default='utf-8')
    type = LabeledChoiceField(choices=AllTypes.choices(), label=_("Type"))
    category = LabeledChoiceField(choices=Category.choices, label=_("Category"))
    protocols = PlatformProtocolSerializer(label=_("Protocols"), many=True, required=False)
    automation = PlatformAutomationSerializer(label=_("Automation"), required=False, default=dict)
    su_method = LabeledChoiceField(
        choices=SU_METHOD_CHOICES, label=_("Su method"),
        required=False, default="sudo", allow_null=True
    )
    custom_fields = PlatformCustomField(label=_("Custom fields"), many=True, required=False)

    class Meta:
        model = Platform
        fields_mini = ["id", "name", "internal"]
        fields_small = fields_mini + [
            "category", "type", "charset",
        ]
        fields_unexport = ['automation']
        read_only_fields = [
            'internal', 'date_created', 'date_updated',
            'created_by', 'updated_by'
        ]
        fields = fields_small + [
            "protocols", "domain_enabled", "su_enabled",
            "su_method", "automation", "comment", "custom_fields",
            "labels"
        ] + read_only_fields
        extra_kwargs = {
            "su_enabled": {"label": _('Su enabled')},
            "domain_enabled": {"label": _('Domain enabled')},
            "domain_default": {"label": _('Default Domain')},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_initial_value()

    def set_initial_value(self):
        if not hasattr(self, 'initial_data'):
            return
        if self.instance:
            return
        if not self.initial_data.get('automation'):
            self.initial_data['automation'] = {}

    @property
    def platform_category_type(self):
        if self.instance:
            return self.instance.category, self.instance.type
        if self.initial_data:
            return self.initial_data.get('category'), self.initial_data.get('type')
        raise serializers.ValidationError({'type': _("type is required")})

    def add_type_choices(self, name, label):
        tp = self.fields['type']
        tp.choices[name] = label
        tp.choice_strings_to_values[name] = label

    @lazyproperty
    def constraints(self):
        category, tp = self.platform_category_type
        constraints = AllTypes.get_constraints(category, tp)
        return constraints

    def validate_protocols(self, protocols):
        if not protocols:
            raise serializers.ValidationError(_("Protocols is required"))
        primary = [p for p in protocols if p.get('primary')]
        if not primary:
            protocols[0]['primary'] = True
        # 这里不设置不行，write_nested 不使用 validated 中的
        self.initial_data['protocols'] = protocols
        return protocols

    def validate_su_enabled(self, su_enabled):
        return su_enabled and self.constraints.get('su_enabled', False)

    def validate_domain_enabled(self, domain_enabled):
        return domain_enabled and self.constraints.get('domain_enabled', False)

    def validate_automation(self, automation):
        automation = automation or {}
        ansible_enabled = automation.get('ansible_enabled', False) \
                          and self.constraints['automation'].get('ansible_enabled', False)
        automation['ansible_enable'] = ansible_enabled
        return automation


class PlatformOpsMethodSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=50, label=_("Name"))
    category = serializers.CharField(max_length=50, label=_("Category"))
    type = serializers.ListSerializer(child=serializers.CharField())
    method = serializers.CharField()
