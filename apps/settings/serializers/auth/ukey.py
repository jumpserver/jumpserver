from collections.abc import Mapping

from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from common.serializers.fields import EncryptedField
from authentication.backends.ukey.vendors import UKeyVendor

__all__ = ['UKeyTestingSerializer', 'UKeySettingSerializer']


def provider_setting_fields(provider):
    return import_string(provider.settings_serializer)().get_fields()


def validate_svs_url(value):
    from authentication.backends.ukey.clients.fisherman import SVSError, parse_service_url

    try:
        parse_service_url(value)
    except SVSError as exc:
        raise serializers.ValidationError(str(exc)) from None


class XJCACASettingSerializer(serializers.Serializer):
    AUTH_UKEY_XJCA_SVS_URL = serializers.CharField(
        required=False, allow_blank=True, max_length=2048, label=_('Fisherman signature verification service URL'),
        validators=[validate_svs_url],
        help_text=_(
            'Enter the full HTTP or HTTPS URL, for example https://svs.example.com:8443. '
            'Do not include an API path or use the password management platform address.'
        ),
    )
    AUTH_UKEY_XJCA_TLS_VERIFY = serializers.ChoiceField(
        choices=[
            ('system', _('Use system trust store')),
            ('custom', _('Use custom CA certificate')),
            ('insecure', _('Ignore certificate verification (unsafe)')),
        ], required=False, label=_('Certificate verification'),
    )
    AUTH_UKEY_XJCA_TLS_CA_CERT = EncryptedField(
        required=False, allow_blank=True, max_length=65536, label=_('HTTPS CA certificate'),
        help_text=_(
            'Upload a PEM CA certificate or certificate chain for the Fisherman HTTPS service, '
            'without a private key (maximum 64 KB). Leave blank to keep the saved certificate. '
            'This does not affect UKey certificate verification.'
        ),
    )


class BuiltinCASettingSerializer(serializers.Serializer):
    AUTH_UKEY_DEFAULT_PIN = EncryptedField(
        min_length=4, max_length=32,
        default='', allow_blank=True, label=_('UKey Default User PIN'),
        help_text=_('UKey default user PIN used for administrator reset')
    )
    # ENROLLMENT SETTINGS
    AUTH_UKEY_ENROLL_ENABLED = serializers.BooleanField(
        default=False, label=_('Enrollment'),
        help_text=_('Whether to enable user certificate enrollment')
    )
    AUTH_UKEY_ENROLL_VALIDITY_DAYS = serializers.IntegerField(
        default=365, label=_('Enrollment Validity Days'), min_value=1,
        help_text=_('Validity period (days) for issued certificates')
    )
    AUTH_UKEY_CA_KEY_CONTENT = EncryptedField(
        default='', allow_blank=True, label=_('CA Key'),
        help_text=_('PEM content of CA private key used for certificate enrollment')
    )
    AUTH_UKEY_CA_CERT_CONTENT = EncryptedField(
        default='', allow_blank=True, label=_('CA Cert'),
        help_text=_('PEM content of CA certificate used for certificate enrollment and authentication')
    )
    AUTH_UKEY_CA_KEY_PASS = EncryptedField(
        default='', allow_blank=True, label=_('CA Key Password'),
        help_text=_('Password for CA private key used for certificate enrollment (leave blank if not set)')
    )


class UKeySettingSerializer(serializers.Serializer):
    PREFIX_TITLE = _('UKey')

    AUTH_UKEY = serializers.BooleanField(default=False, label=_('UKey'))
    AUTH_UKEY_VENDOR = serializers.ChoiceField(
        choices=UKeyVendor.choices, required=False, label=_('UKey vendor'),
        help_text=_('Select the vendor of your UKey. After switching, refresh UKey pages and restart unfinished operations.'),
    )
    AUTH_UKEY_CA_PROVIDER = serializers.ChoiceField(
        choices=[], default='builtin', label=_('CA provider'),
    )
    AUTH_UKEY_CA_PROVIDERS = serializers.SerializerMethodField()
    AUTH_UKEY_CONFIG_REVISION = serializers.CharField(required=False, max_length=32)
    AUTH_UKEY_CHALLENGE_TTL = serializers.IntegerField(
        default=300, min_value=60, max_value=3600, label=_('Challenge TTL (seconds)'),
        help_text=_('Time-to-live (seconds) for authentication challenge codes'),
    )
    AUTH_UKEY_CA_CERT_ALGORITHM = serializers.SerializerMethodField(
        label=_('CA Cert Algorithm')
    )

    def get_fields(self):
        from authentication.backends.ukey.providers import get_provider_classes

        fields = super().get_fields()
        providers = get_provider_classes()
        fields['AUTH_UKEY_CA_PROVIDER'].choices = [(provider.id, provider.label) for provider in providers]
        for provider in providers:
            provider_fields = provider_setting_fields(provider)
            duplicate = fields.keys() & provider_fields.keys()
            if duplicate:
                raise ImproperlyConfigured(f'Duplicate UKey provider settings: {", ".join(sorted(duplicate))}')
            fields.update(provider_fields)
        return fields

    def get_AUTH_UKEY_CA_PROVIDERS(self, obj):
        from authentication.backends.ukey.providers import get_provider_classes

        capabilities = (
            'supports_enrollment', 'supports_connection_test', 'binding_mode',
            'requires_certificate_selection', 'expose_default_pin',
        )
        return [{
            'id': provider.id,
            'label': str(provider.label),
            'fields': list(provider.display_fields or provider_setting_fields(provider)),
            'secret_fields': sorted(provider.secret_fields),
            'connection_fields': list(provider.connection_fields),
            'supported_vendors': list(provider.supported_vendors or UKeyVendor.values),
            **{name: getattr(provider, name) for name in capabilities},
        } for provider in get_provider_classes()]

    def get_AUTH_UKEY_CA_CERT_ALGORITHM(self, obj):
        from authentication.backends.ukey.providers import get_provider_classes
        # Settings must remain readable so administrators can repair an invalid selection.
        provider_class = next((p for p in get_provider_classes() if p.id == obj.get('AUTH_UKEY_CA_PROVIDER')), None)
        if provider_class is None:
            return _('Unknown')
        provider = provider_class(obj)
        return provider.algorithm_label or provider.ca_algorithm or _('Auto-Detect After Upload')

    def validate(self, attrs):
        from authentication.backends.ukey.configuration import SECRET_FIELDS, get_snapshot
        from authentication.backends.ukey.exceptions import UKeyAuthError
        from authentication.backends.ukey.providers import get_provider, get_provider_classes

        merged = dict(self.context.get('snapshot') or get_snapshot())
        merged.update({key: value for key, value in attrs.items()
                       if not (key in SECRET_FIELDS and value in ('', None))})
        provider_class = next((p for p in get_provider_classes() if p.id == merged['AUTH_UKEY_CA_PROVIDER']), None)
        if (provider_class and provider_class.supported_vendors
                and merged['AUTH_UKEY_VENDOR'] not in provider_class.supported_vendors):
            raise serializers.ValidationError({'AUTH_UKEY_VENDOR': _(
                'This certificate authentication method does not support the selected UKey vendor.'
            )})
        try:
            get_provider(merged).validate_config()
        except UKeyAuthError as exc:
            raise serializers.ValidationError(str(exc)) from None
        return attrs


class UKeyTestingSerializer(serializers.Serializer):
    AUTH_UKEY_CA_PROVIDER = serializers.ChoiceField(choices=[], required=False)
    AUTH_UKEY_VENDOR = serializers.ChoiceField(choices=UKeyVendor.choices, required=False)

    def get_fields(self):
        from authentication.backends.ukey.configuration import get_snapshot
        from authentication.backends.ukey.exceptions import UKeyAuthError
        from authentication.backends.ukey.providers import get_provider, get_provider_classes

        fields = super().get_fields()
        selector = fields['AUTH_UKEY_CA_PROVIDER']
        selector.choices = [(provider.id, provider.label) for provider in get_provider_classes()]
        snapshot = dict(self.context.get('snapshot') or get_snapshot())
        data = getattr(self, 'initial_data', {})
        if isinstance(data, Mapping) and 'AUTH_UKEY_VENDOR' in data:
            try:
                snapshot['AUTH_UKEY_VENDOR'] = fields['AUTH_UKEY_VENDOR'].run_validation(data['AUTH_UKEY_VENDOR'])
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({'AUTH_UKEY_VENDOR': exc.detail}) from None
        if isinstance(data, Mapping) and 'AUTH_UKEY_CA_PROVIDER' in data:
            try:
                snapshot['AUTH_UKEY_CA_PROVIDER'] = selector.run_validation(data['AUTH_UKEY_CA_PROVIDER'])
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({'AUTH_UKEY_CA_PROVIDER': exc.detail}) from None
        try:
            provider = get_provider(snapshot)
        except UKeyAuthError as exc:
            raise serializers.ValidationError({'AUTH_UKEY_VENDOR': str(exc)}) from None
        settings_fields = provider_setting_fields(provider)
        fields.update({name: settings_fields[name] for name in provider.connection_fields})
        self.provider = provider
        return fields

    def validate(self, attrs):
        if not self.provider.supports_connection_test:
            raise serializers.ValidationError(_('This CA provider does not support connection testing.'))
        unknown = self.initial_data.keys() - self.fields.keys()
        if unknown:
            raise serializers.ValidationError({name: _('Unknown connection field.') for name in sorted(unknown)})
        # Blank write-only credentials mean "keep saved", just as on settings save.
        for name in self.provider.secret_fields:
            if attrs.get(name) in ('', None):
                attrs.pop(name, None)
        return attrs
