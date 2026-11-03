"""JiDa's existing JIT Key client with remote VCTK_S verification."""
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from ..verifiers.vctk_s import (
    VCTKSCAConfigError, VCTKSVerifier, certificate_algorithm, load_issuing_cas,
)
from .base import BaseCAProvider


class VCTKSCAProvider(BaseCAProvider):
    id = 'vctk_s'
    label = 'VCTK_S'
    binding_mode = 'certificate'
    sdk_profile = 'sdk_config_vctk_s.yaml'
    uses_one_time_challenge = True
    supported_vendors = ('ji_da',)
    supports_connection_test = True
    expose_default_pin = False
    sdk_sign_method = 'UKey_P7SignAttach'
    sdk_digest_from_certificate = True
    settings_serializer = 'settings.serializers.auth.ukey.VCTKSCASettingSerializer'
    secret_fields = (
        'AUTH_UKEY_VCTK_S_TLS_CA_CERT', 'AUTH_UKEY_VCTK_S_ISSUING_CA',
        'AUTH_UKEY_VCTK_S_PASSWORD',
    )
    connection_fields = (
        'AUTH_UKEY_VCTK_S_SVS_URL', 'AUTH_UKEY_VCTK_S_TLS_VERIFY',
        'AUTH_UKEY_VCTK_S_TLS_CA_CERT',
        'AUTH_UKEY_VCTK_S_USERNAME', 'AUTH_UKEY_VCTK_S_PASSWORD',
    )
    display_fields = connection_fields + ('AUTH_UKEY_VCTK_S_ISSUING_CA',)

    @property
    def ca_algorithm(self):
        try:
            issuers = load_issuing_cas(self.snapshot.get('AUTH_UKEY_VCTK_S_ISSUING_CA', ''))
        except VCTKSCAConfigError:
            return ''
        return ' / '.join(sorted({certificate_algorithm(issuer).upper() for issuer in issuers}))

    @property
    def verifier(self):
        return VCTKSVerifier(
            self.snapshot.get('AUTH_UKEY_VCTK_S_SVS_URL', ''),
            issuing_ca=self.snapshot.get('AUTH_UKEY_VCTK_S_ISSUING_CA', ''),
            tls_verify=self.snapshot.get('AUTH_UKEY_VCTK_S_TLS_VERIFY', 'system'),
            tls_ca_cert=self.snapshot.get('AUTH_UKEY_VCTK_S_TLS_CA_CERT', ''),
            connect_timeout=self.snapshot.get('AUTH_UKEY_VCTK_S_CONNECT_TIMEOUT', 3),
            read_timeout=self.snapshot.get('AUTH_UKEY_VCTK_S_READ_TIMEOUT', 5),
            username=self.snapshot.get('AUTH_UKEY_VCTK_S_USERNAME', ''),
            password=self.snapshot.get('AUTH_UKEY_VCTK_S_PASSWORD', ''),
        )

    def validate_config(self):
        if not self.snapshot['AUTH_UKEY']:
            return
        for field in ('AUTH_UKEY_VCTK_S_SVS_URL', 'AUTH_UKEY_VCTK_S_ISSUING_CA'):
            if not self.snapshot.get(field):
                raise ValidationError({field: _('This field is required.')})
        if (self.snapshot['AUTH_UKEY_VCTK_S_SVS_URL'].lower().startswith('https://')
                and self.snapshot.get('AUTH_UKEY_VCTK_S_TLS_VERIFY', 'system') == 'custom'
                and not self.snapshot.get('AUTH_UKEY_VCTK_S_TLS_CA_CERT')):
            raise ValidationError({'AUTH_UKEY_VCTK_S_TLS_CA_CERT': _('A CA certificate is required.')})
        try:
            self.verifier.validate_config()
        except VCTKSCAConfigError as exc:
            raise ValidationError({'AUTH_UKEY_VCTK_S_ISSUING_CA': str(exc)}) from None

    def test_connection(self):
        return self.verifier.test_connection()

    def generate_challenge(self):
        return self.verifier.generate_challenge()
