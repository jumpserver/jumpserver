from django.utils.translation import gettext_lazy as _

from ..exceptions import UKeyAuthError
from ..vendors import UKeyVendor


class BaseCAProvider:
    """Trusted, in-tree certificate adapter; never owns users or login sessions."""

    id = ''
    label = ''
    binding_mode = 'certificate'
    supported_vendors = None
    supports_enrollment = False
    supports_connection_test = False
    requires_certificate_selection = False
    expose_default_pin = False
    sdk_profile = None
    algorithm_label = None
    settings_serializer = ''
    display_fields = ()
    secret_fields = ()
    connection_fields = ()

    def __init__(self, snapshot):
        self.snapshot = snapshot

    @property
    def capabilities(self):
        return {
            'binding_mode': self.binding_mode,
            'supports_enrollment': self.supports_enrollment,
            'supports_connection_test': self.supports_connection_test,
            'requires_certificate_selection': self.requires_certificate_selection,
            'expose_default_pin': self.expose_default_pin,
        }

    def validate_vendor(self):
        if self.snapshot['AUTH_UKEY_VENDOR'] not in UKeyVendor.values:
            raise UKeyAuthError(_('Unsupported UKey vendor. Select a supported vendor in UKey settings.'))
        if self.supported_vendors is not None and self.snapshot['AUTH_UKEY_VENDOR'] not in self.supported_vendors:
            raise UKeyAuthError(_('This certificate authentication method does not support the selected UKey vendor.'))

    @property
    def ca_algorithm(self):
        raise NotImplementedError

    def validate_config(self):
        raise NotImplementedError

    def generate_challenge(self):
        """Return the exact message to sign; the core owns TTL and one-use claims."""
        raise NotImplementedError

    @property
    def verifier(self):
        """Build the compatible verifier from this request's configuration snapshot."""
        raise NotImplementedError

    def verify_proof(self, cert, signature, challenge, username=''):
        """Verify first, then return certificate claims, never an application user."""
        return self.verifier.verify_proof(cert, signature, challenge, username)

    def enroll(self, csr):
        raise UKeyAuthError('Certificate enrollment is not supported by this CA provider')

    def test_connection(self):
        raise UKeyAuthError('Connection testing is not supported by this CA provider')
