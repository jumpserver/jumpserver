import hashlib

from django.utils.translation import gettext_lazy as _

from ..exceptions import UKeyAuthError, UKeyServiceError
from ..clients.fisherman import (
    MAX_CERT, MAX_SIGNATURE, FishermanClient, SVSError, decode_base64,
    load_certificate, log_failure,
)
from .base import BaseVerifier


class FishermanVerifier(BaseVerifier):
    """Certificate proofs through the direct Fisherman signature verification service."""

    def __init__(self, url, *, tls_verify='system', tls_ca_cert='', connect_timeout=3, read_timeout=5):
        self.connection = {
            'url': url, 'tls_verify': tls_verify, 'tls_ca_cert': tls_ca_cert,
            'connect_timeout': connect_timeout, 'read_timeout': read_timeout,
        }

    def _client(self):
        return FishermanClient(**self.connection)

    def validate_config(self):
        try:
            self._client()
        except (SVSError, UnicodeError):
            raise UKeyAuthError(_(
                'Check the Fisherman signature verification service URL and HTTPS certificate settings.'
            )) from None

    def generate_random(self):
        # Keep the service's random text unchanged as the signing challenge.
        try:
            return self._client().generate_random()
        except SVSError as exc:
            raise UKeyServiceError(str(exc)) from None

    def verify_proof(self, cert, signature, challenge, username=''):
        try:
            cert_der = decode_base64(cert, MAX_CERT)
        except Exception as exc:
            log_failure(exc, 'verify_proof', 'certificate_parse')
            if not isinstance(exc, SVSError):
                raise
            raise UKeyAuthError(_(
                'Unable to parse the UKey certificate. Contact the administrator.'
            )) from None
        try:
            decode_base64(signature, MAX_SIGNATURE)
        except Exception as exc:
            log_failure(exc, 'verify_proof', 'signature_parse')
            if not isinstance(exc, SVSError):
                raise
            raise UKeyAuthError(_(
                'Unable to parse the UKey signature. Contact the administrator.'
            )) from None
        stage = 'challenge_encode'
        try:
            message = challenge.encode('ascii')
            stage = 'verify_signature'
            self._client().verify_signed_data(cert, message, signature)
            # Only read binding identity after SVS accepts the original proof.
            # Certificate validity/trust and signature checks belong to SVS.
            stage = 'certificate_identity'
            certificate = load_certificate(cert_der)
            serial = format(certificate.serial_number, 'x')
            if len(serial) > 64:
                raise UKeyAuthError(_('Invalid certificate serial number'))
            issuer = certificate.issuer.dump() + (certificate.authority_key_identifier or b'')
            return {
                'issuer_fingerprint': hashlib.sha256(issuer).hexdigest(),
                'serial_number': serial,
                'certificate_fingerprint': hashlib.sha256(cert_der).hexdigest(),
            }
        except Exception as exc:
            log_failure(exc, 'verify_proof', stage)
            if stage == 'certificate_identity' and isinstance(exc, (
                ValueError, TypeError, KeyError, IndexError, OverflowError, RecursionError,
            )):
                raise UKeyAuthError(_(
                    'Unable to parse the UKey certificate. Contact the administrator.'
                )) from None
            if not isinstance(exc, (SVSError, UnicodeError)):
                raise
            if isinstance(exc, SVSError):
                raise UKeyServiceError(str(exc)) from None
            raise UKeyAuthError(_('Invalid certificate data')) from None

    def test_connection(self):
        try:
            self._client().generate_random()
        except SVSError as exc:
            if exc.resp_value is not None:
                raise UKeyServiceError(str(exc)) from None
            raise UKeyAuthError(_(
                'Cannot connect to the Fisherman signature verification service or obtain random data. Check the settings and try again.'
            )) from None
        return {
            'connection': True,
            'random': True,
            'msg': _(
                'Fisherman signature verification service connection and random-data checks passed. '
                'UKey login and certificate verification have not been tested. Settings were not saved.'
            ),
        }
