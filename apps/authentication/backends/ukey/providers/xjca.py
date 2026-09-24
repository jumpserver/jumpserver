from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from ..verifiers.fisherman import FishermanVerifier
from .base import BaseCAProvider


class XJCACAProvider(BaseCAProvider):
    id = 'xjca'
    label = _('Xinjiang CA')
    supported_vendors = ('long_mai',)
    supports_connection_test = True
    requires_certificate_selection = True
    sdk_profile = 'sdk_config_xjca.yaml'
    algorithm_label = 'SM2/SM3'
    settings_serializer = 'settings.serializers.auth.ukey.XJCACASettingSerializer'
    secret_fields = frozenset({'AUTH_UKEY_XJCA_TLS_CA_CERT'})
    connection_fields = (
        'AUTH_UKEY_XJCA_SVS_URL', 'AUTH_UKEY_XJCA_TLS_VERIFY', 'AUTH_UKEY_XJCA_TLS_CA_CERT',
    )
    display_fields = connection_fields

    @property
    def ca_algorithm(self):
        return 'SM2'

    @property
    def verifier(self):
        return FishermanVerifier(
            self.snapshot['AUTH_UKEY_XJCA_SVS_URL'],
            tls_verify=self.snapshot['AUTH_UKEY_XJCA_TLS_VERIFY'],
            tls_ca_cert=self.snapshot['AUTH_UKEY_XJCA_TLS_CA_CERT'],
            connect_timeout=self.snapshot['AUTH_UKEY_XJCA_CONNECT_TIMEOUT'],
            read_timeout=self.snapshot['AUTH_UKEY_XJCA_READ_TIMEOUT'],
        )

    def validate_config(self):
        # Disabling authentication must remain possible after the issuing CA expires.
        if not self.snapshot['AUTH_UKEY']:
            return
        if not self.snapshot['AUTH_UKEY_XJCA_SVS_URL']:
            raise ValidationError({'AUTH_UKEY_XJCA_SVS_URL': _('This field is required.')})
        if (self.snapshot['AUTH_UKEY_XJCA_SVS_URL'].lower().startswith('https://')
                and self.snapshot['AUTH_UKEY_XJCA_TLS_VERIFY'] == 'custom'
                and not self.snapshot['AUTH_UKEY_XJCA_TLS_CA_CERT']):
            raise ValidationError({'AUTH_UKEY_XJCA_TLS_CA_CERT': _('A CA certificate is required.')})
        self.verifier.validate_config()

    def generate_challenge(self):
        return self.verifier.generate_random()

    def test_connection(self):
        return self.verifier.test_connection()
