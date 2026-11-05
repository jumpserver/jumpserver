"""Verify existing JiDa UKey identities through the VCTK_S HTTP service."""
import hashlib
import re
from datetime import datetime, timezone

from asn1crypto import cms, core
from django.utils.translation import gettext_lazy as _

from common.utils import get_logger
from ..clients.fisherman import (
    Certificate, MAX_CERT, SM2_OID, SVSError, decode_base64, strict_der,
)
from ..clients.vctk_s import MAX_P7_SIZE, VCTKSClient
from ..exceptions import UKeyAuthError, UKeyServiceError
from .base import BaseVerifier

logger = get_logger(__name__)

SIGNED_DATA_OIDS = {'1.2.840.113549.1.7.2', '1.2.156.10197.6.1.4.2.2'}
DATA_OIDS = {'1.2.840.113549.1.7.1', '1.2.156.10197.6.1.4.2.1'}
SM3_OID = '1.2.156.10197.1.401'
SHA256_OID = '2.16.840.1.101.3.4.2.1'


class CertificatePolicyError(ValueError):
    """A safe, localized reason that contains no certificate contents."""


class VCTKSCertificateChoices(cms.CertificateChoices):
    _alternatives = [('certificate', Certificate), *cms.CertificateChoices._alternatives[1:]]


class VCTKSCertificateSet(cms.CertificateSet):
    _child_spec = VCTKSCertificateChoices


class VCTKSDataContentInfo(cms.ContentInfo):
    _oid_specs = {**cms.ContentInfo._oid_specs, '1.2.156.10197.6.1.4.2.1': core.OctetString}


class VCTKSSignedData(cms.SignedData):
    _fields = [(name, VCTKSCertificateSet if name == 'certificates' else spec, *options)
               for name, spec, *options in cms.SignedData._fields]

    def _encap_content_info_spec(self):
        return VCTKSDataContentInfo if self['version'].native == 'v1' else cms.EncapsulatedContentInfo

    _spec_callbacks = {'encap_content_info': _encap_content_info_spec}


class VCTKSContentInfo(cms.ContentInfo):
    # The vendor's GM P7 envelope uses GM/T 0010 content OIDs. Keep these
    # mappings local; changing asn1crypto's global maps would affect other CAs.
    _oid_specs = {
        **cms.ContentInfo._oid_specs,
        'signed_data': VCTKSSignedData,
        '1.2.156.10197.6.1.4.2.2': VCTKSSignedData,
    }


def load_signed_der(cls, data):
    """Preserve signed bytes while accepting the vendor's explicit CA=false."""
    value = cls.load(data, strict=True)
    value.native
    if len(value) != len(cls._fields):
        raise ValueError('Unexpected signed data members')

    canonical = cls.load(data, strict=True).dump(force=True)
    if canonical == data:
        return value

    # Normalize only a comparison copy. Re-encoding the original certificate
    # would change its signed content and its binding fingerprint.
    comparison = cls.load(data, strict=True)
    if cls is Certificate:
        certificates = [(None, comparison)]
    elif comparison['content_type'].dotted in SIGNED_DATA_OIDS:
        certificates = [
            (index, item.chosen) for index, item in enumerate(comparison['content']['certificates'])
            if item.name == 'certificate'
        ]
    else:
        certificates = []
    for index, certificate in certificates:
        changed = False
        for extension in certificate['tbs_certificate']['extensions']:
            if (extension['extn_id'].native == 'basic_constraints'
                    and extension['extn_value'].contents == b'\x30\x03\x01\x01\x00'):
                extension['extn_value'] = {'ca': False}
                changed = True
        if changed and index is not None:
            comparison['content']['certificates'][index] = VCTKSCertificateChoices(
                name='certificate', value=certificate,
            )
    if comparison.dump() != canonical:
        raise ValueError('Unsupported signed data encoding')
    return value


def certificate_algorithm(certificate):
    algorithm = certificate['tbs_certificate']['subject_public_key_info']['algorithm']
    if algorithm['algorithm'].native == 'rsa':
        return 'rsa'
    if (algorithm['algorithm'].dotted == SM2_OID
            or (algorithm['algorithm'].native == 'ec'
                and algorithm['parameters'].native == SM2_OID)):
        return 'sm2'
    raise CertificatePolicyError(_('Unsupported issuing CA or signing certificate algorithm'))


def check_certificate_validity(certificate):
    validity = certificate['tbs_certificate']['validity']
    if not validity['not_before'].native <= datetime.now(timezone.utc) <= validity['not_after'].native:
        raise ValueError(_('Certificate has expired or is not yet valid'))


def checked_certificate(data, *, ca=False, check_time=True):
    if not isinstance(data, bytes) or not 1 <= len(data) <= MAX_CERT:
        raise ValueError('Invalid certificate size')
    certificate = strict_der(Certificate, data) if ca else load_signed_der(Certificate, data)
    certificate_algorithm(certificate)
    extensions = certificate['tbs_certificate']['extensions']
    extension_ids = [extension['extn_id'].dotted for extension in extensions]
    if len(extension_ids) != len(set(extension_ids)):
        raise CertificatePolicyError(_('Duplicate certificate extension'))
    if bool(certificate.ca) != ca:
        raise CertificatePolicyError(_('Incorrect certificate role (CA or user certificate)'))
    usage = certificate.key_usage_value
    if usage is not None and ('key_cert_sign' if ca else 'digital_signature') not in usage.native:
        raise CertificatePolicyError(_('Incorrect certificate key usage'))
    if check_time:
        check_certificate_validity(certificate)
    return certificate


def _signer_matches(sid, certificate):
    if sid.name == 'issuer_and_serial_number':
        return (sid.chosen['issuer'].dump() == certificate.issuer.dump()
                and sid.chosen['serial_number'].native == certificate.serial_number)
    return (sid.name == 'subject_key_identifier' and certificate.key_identifier is not None
            and sid.chosen.native == certificate.key_identifier)


def check_attached_signer(signature, certificate, message):
    if not isinstance(signature, bytes) or not 1 <= len(signature) <= MAX_P7_SIZE:
        raise ValueError('Invalid P7 signature size')
    content = load_signed_der(VCTKSContentInfo, signature)
    if content['content_type'].dotted not in SIGNED_DATA_OIDS:
        raise ValueError('Attached SignedData required')
    signed = content['content']
    encapsulated = signed['encap_content_info']
    if (encapsulated['content_type'].dotted not in DATA_OIDS
            or encapsulated['content'].native != message):
        raise ValueError('Attached content differs from challenge')
    signers = signed['signer_infos']
    if len(signers) != 1:
        raise ValueError('Exactly one signer required')
    signer = signers[0]
    # A P7 may include a certificate chain. Resolve its signer, rather than
    # assuming the first (or only) certificate belongs to the UKey.
    matches = [
        item.chosen for item in signed['certificates']
        if item.name == 'certificate' and _signer_matches(signer['sid'], item.chosen)
    ]
    if len(matches) != 1 or matches[0].dump() != certificate.dump():
        raise ValueError('P7 signer differs from submitted certificate')
    expected_digest = SM3_OID if certificate_algorithm(certificate) == 'sm2' else SHA256_OID
    if (signer['digest_algorithm']['algorithm'].dotted != expected_digest
            or {item['algorithm'].dotted for item in signed['digest_algorithms']} != {expected_digest}
            or not signer['signature'].native):
        raise ValueError('Incorrect P7 signing algorithm')
    return 'sm3' if expected_digest == SM3_OID else 'sha256'


class VCTKSVerifier(BaseVerifier):
    def __init__(self, url='', *, tls_verify='system', tls_ca_cert='',
                 connect_timeout=3, read_timeout=5, username='', password=''):
        self.connection = dict(
            url=url, tls_verify=tls_verify, tls_ca_cert=tls_ca_cert,
            connect_timeout=connect_timeout, read_timeout=read_timeout,
            username=username, password=password,
        )

    def _client(self):
        return VCTKSClient(**self.connection)

    def validate_config(self):
        try:
            self._client()
        except Exception:
            raise UKeyAuthError(_(
                'Check the VCTK_S service URL, business authorization and HTTPS trust settings.'
            )) from None

    def verify_proof(self, cert, signature, challenge, username=''):
        stage = 'parse'
        try:
            if not isinstance(challenge, str) or not re.fullmatch('[0-9a-f]{64}', challenge):
                raise ValueError('Invalid challenge')
            certificate = checked_certificate(decode_base64(cert, MAX_CERT))
            signature_bytes = decode_base64(signature, MAX_P7_SIZE)
            stage = 'signer_identity'
            digest = check_attached_signer(signature_bytes, certificate, challenge.encode('ascii'))
            serial = format(certificate.serial_number, 'x')
            if len(serial) > 64:
                raise ValueError('Invalid certificate serial number')
        except UKeyAuthError:
            raise
        except Exception as exc:
            logger.warning('VCTK_S proof rejected: stage=%s exception=%s', stage, type(exc).__name__)
            raise UKeyAuthError(_('VCTK_S certificate or signature verification failed.')) from None
        try:
            # The VCTK_S service validates certificate trust and the signature.
            # Bind its authenticated result to the exact proof checked above.
            result = self._client().verify_signed_data(signature, digest)
            if (result['plain'] != challenge.encode('ascii')
                    or result['certificate'] != certificate.dump()):
                raise ValueError('Returned content or certificate differs from submitted proof')
        except Exception as exc:
            logger.warning('VCTK_S proof rejected: stage=server exception=%s', type(exc).__name__)
            raise UKeyServiceError(_('VCTK_S server verification failed. Check the service settings.')) from None
        issuer = certificate.issuer.dump() + (certificate.authority_key_identifier or b'')
        return {
            'issuer_fingerprint': hashlib.sha256(issuer).hexdigest(),
            'serial_number': serial,
            'certificate_fingerprint': hashlib.sha256(certificate.dump()).hexdigest(),
        }

    def generate_challenge(self):
        try:
            return self._client().generate_random().hex()
        except SVSError as exc:
            raise UKeyServiceError(str(exc)) from None

    def test_connection(self):
        self.generate_challenge()
        return {
            'connection': True, 'verification': False,
            'msg': _('VCTK_S random generation check passed. UKey signature and certificate verification '
                     'have not been tested. Settings were not saved.'),
        }
