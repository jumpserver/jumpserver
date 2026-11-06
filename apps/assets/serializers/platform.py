from django.conf import settings
from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from assets.models import Asset
from common.serializers import (
    WritableNestedModelSerializer, type_field_map, MethodSerializer,
    DictSerializer, create_serializer_class, ResourceLabelsMixin,
    CommonSerializerMixin
)
from common.serializers.fields import LabeledChoiceField, ObjectRelatedField
from ..const import Category, AllTypes, Protocol, SuMethodChoices
from ..models import Platform, PlatformProtocol, PlatformAutomation

__all__ = [
    "PlatformSerializer", "PlatformOpsMethodSerializer", "PlatformProtocolSerializer",
    "PlatformProtocolCreateSerializer", "PlatformListSerializer",
]


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
            "remove_account_enabled", "remove_account_method", "remove_account_params",
        ]
        extra_kwargs = {
            # 启用资产探测
            "ping_enabled": {"label": _("Ping enabled"), "help_text": _("Enable asset detection")},
            "ping_method": {"label": _("Ping method")},
            "gather_facts_enabled": {
                "label": _("Gather facts enabled"),
                "help_text": _("Enable asset information collection")
            },
            "gather_facts_method": {
                "label": _("Gather facts method"),
            },
            "verify_account_enabled": {
                "label": _("Verify account enabled"),
                "help_text": _("Enable account verification")
            },
            "verify_account_method": {
                "label": _("Verify account method"),
            },
            "change_secret_enabled": {
                "label": _("Change secret enabled"),
                "help_text": _("Enable account secret auto change")
            },
            "change_secret_method": {
                "label": _("Change secret method"),
            },
            "push_account_enabled": {
                "label": _("Push account enabled"),
                "help_text": _("Enable account auto push")
            },
            "push_account_method": {
                "label": _("Push account method"),
            },
            "gather_accounts_enabled": {
                "label": _("Gather accounts enabled"),
                "help_text": _("Enable account collection")
            },
            "gather_accounts_method": {
                "label": _("Gather accounts method"),
            },
            "remove_account_method": {
                "label": _("Remove account method"),
            },
            "remove_account_enabled": {
                "label": _("Remove accounts enabled"),
                "help_text": _("Enable account remove"),
            },

        }


class PlatformProtocolSerializer(serializers.ModelSerializer):
    setting = MethodSerializer(required=False, label=_("Setting"))
    port_from_addr = serializers.BooleanField(label=_("Port from addr"), read_only=True)
    port = serializers.IntegerField(label=_("Port"), required=False, min_value=0, max_value=65535)

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
        if protocol in ('http', 'https') and not settings.XPACK_LICENSE_IS_VALID:
            for field in setting_fields:
                if field['name'] == 'autofill':
                    field['choices'] = [(key, label) for key, label in field['choices'] if key != 'script']
        name = '{}ProtocolSettingSerializer'.format(protocol.capitalize())
        return create_serializer_class(name, setting_fields)()

    def to_file_representation(self, data):
        return '{name}/{port}'.format(**data)

    def to_file_internal_value(self, data):
        name, port = data.split('/')
        return {'name': name, 'port': port}

    @staticmethod
    def get_render_help_text():
        return _('Protocols, format is ["protocol/port"]')


class PlatformProtocolCreateSerializer(PlatformProtocolSerializer):
    platform = serializers.PrimaryKeyRelatedField(
        queryset=Platform.objects.all(), pk_field=serializers.IntegerField()
    )
    port = serializers.IntegerField(label=_("Port"), min_value=0, max_value=65535)

    class Meta(PlatformProtocolSerializer.Meta):
        fields = PlatformProtocolSerializer.Meta.fields + ['platform']


class PlatformCustomField(serializers.Serializer):
    TYPE_CHOICES = [(t, t) for t, c in type_field_map.items()]
    name = serializers.CharField(label=_("Name"), max_length=128)
    label = serializers.CharField(label=_("Label"), max_length=128)
    type = serializers.ChoiceField(choices=TYPE_CHOICES, label=_("Type"), default='str')
    default = serializers.CharField(default="", allow_blank=True, label=_("Default"), max_length=1024)
    help_text = serializers.CharField(default="", allow_blank=True, label=_("Help text"), max_length=1024)
    choices = serializers.ListField(default=list, label=_("Choices"), required=False)


class PlatformSerializer(ResourceLabelsMixin, CommonSerializerMixin, WritableNestedModelSerializer):
    id = serializers.IntegerField(
        label='ID', required=False,
        validators=[UniqueValidator(queryset=Platform.objects.all())]
    )
    charset = LabeledChoiceField(choices=Platform.CharsetChoices.choices, label=_("Charset"), default='utf-8')
    type = LabeledChoiceField(choices=AllTypes.choices(), label=_("Type"))
    category = LabeledChoiceField(choices=Category.choices, label=_("Category"))
    protocols = PlatformProtocolSerializer(label=_("Protocols"), many=True, required=False)
    automation = PlatformAutomationSerializer(label=_("Automation"), required=False)
    su_method = LabeledChoiceField(
        choices=SuMethodChoices.choices, label=_("Su method"),
        required=False, default=SuMethodChoices.sudo, allow_null=True
    )
    custom_fields = PlatformCustomField(label=_("Custom fields"), many=True, required=False)
    assets = ObjectRelatedField(queryset=Asset.objects, many=True, required=False, label=_('Assets'))
    assets_amount = serializers.IntegerField(label=_('Assets amount'), read_only=True)
    has_package = serializers.SerializerMethodField(label=_('Has package'))

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
        fields_m2m = ['assets', 'assets_amount']
        fields = fields_small + fields_m2m + [
            "protocols", "gateway_enabled", "su_enabled", "su_method",
            "ds_enabled", "automation", "comment", "custom_fields", "labels", "has_package"
        ] + read_only_fields
        extra_kwargs = {
            "su_enabled": {
                "label": _('Su enabled'),
                "help_text": _(
                    "Login with account when accessing assets, then automatically switch to another, "
                    "similar to logging in with a regular account and then switching to root"
                )
            },
            "gateway_enabled": {
                "label": _('Gateway enabled'),
                "help_text": _("Assets can be connected using a zone gateway")
            },
            "zone_default": {"label": _('Default zone')},
            'assets': {'required': False, 'label': _('Assets')},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_initial_value()

    def set_initial_value(self):
        if not isinstance(getattr(self, 'initial_data', None), dict):
            return

        self.initial_data = self.initial_data.copy()
        name = self.initial_data.get('name')
        if isinstance(name, str) and ' ' in name:
            self.initial_data['name'] = name.replace(' ', '-')

        if self.instance:
            return
        if 'automation' not in self.initial_data:
            self.initial_data['automation'] = {}

    def add_type_choices(self, name, label):
        tp = self.fields['type']
        tp.choices[name] = label
        tp.choice_strings_to_values[name] = label

    @staticmethod
    def get_has_package(obj):
        return bool(obj.package_id and obj.package.exists)

    def validate_protocols(self, protocols):
        if not protocols:
            raise serializers.ValidationError(_("Protocols is required"))
        primary = [p for p in protocols if p.get('primary')]
        if not primary:
            protocols[0]['primary'] = True
        # 这里不设置不行，write_nested 不使用 validated 中的
        self.initial_data['protocols'] = protocols
        return protocols

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # Cross-field constraints must run after required fields and choice
        # objects have been validated and converted to their scalar values.
        category = attrs.get('category', getattr(self.instance, 'category', None))
        tp = attrs.get('type', getattr(self.instance, 'type', None))
        constraints = AllTypes.get_constraints(category, tp)
        for name in ('su_enabled', 'gateway_enabled'):
            if name in attrs:
                attrs[name] = attrs[name] and constraints.get(name, False)
        automation = attrs.get('automation', {})
        if 'ansible_enabled' in automation:
            automation['ansible_enabled'] = (
                automation['ansible_enabled']
                and constraints.get('automation', {}).get('ansible_enabled', False)
            )
            # drf-writable-nested validates reverse relations again from the
            # initial input, so carry the constrained value into that input.
            self.initial_data['automation']['ansible_enabled'] = automation['ansible_enabled']
        return attrs


class PlatformListSerializer(PlatformSerializer):
    class Meta(PlatformSerializer.Meta):
        fields = list(set(PlatformSerializer.Meta.fields + ['assets_amount']) - {'assets'})


class PlatformOpsMethodSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=50, label=_("Name"))
    category = serializers.CharField(max_length=50, label=_("Category"))
    type = serializers.ListSerializer(child=serializers.CharField())
    method = serializers.CharField()
