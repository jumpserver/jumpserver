"""P7 signer binding and real RSA certificate checks, without vendor hardware."""
import base64
import hashlib
from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import MagicMock, patch

from asn1crypto import algos, cms, keys, x509 as asn1_x509
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import pkcs7

from authentication.backends.ukey.clients.fisherman import Certificate, SVSError
from authentication.backends.ukey.clients.vctk_s import MAX_P7_SIZE
from authentication.backends.ukey.exceptions import (
    UKeyAuthError, UKeyCertChainError, UKeyCertCNMismatchError, UKeyServiceError,
    UKeySignatureError,
)
from authentication.backends.ukey.verifiers import vctk_s
from authentication.backends.ukey.verifiers.builtin import BuiltinVerifier


CHALLENGE = 'a1' * 32
URL = 'http://192.168.10.5:8000'


def encode(data):
    return base64.b64encode(data).decode('ascii')


def issue_certificate(key, *, issuer_key=None, issuer=None, name='user', ca=False,
                      serial=123, start=-1, end=1, explicit_ca_false=False):
    now = datetime.now(timezone.utc)
    subject = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, name)])
    issuer_key = issuer_key or key
    return (
        x509.CertificateBuilder().subject_name(subject).issuer_name(issuer.subject if issuer else subject)
        .serial_number(serial).public_key(key.public_key())
        .not_valid_before(now + timedelta(days=start)).not_valid_after(now + timedelta(days=end))
        .add_extension(
            x509.UnrecognizedExtension(x509.ExtensionOID.BASIC_CONSTRAINTS, b'\x30\x03\x01\x01\x00')
            if explicit_ca_false else x509.BasicConstraints(ca=ca, path_length=None),
            critical=True,
        )
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(issuer_key.public_key()), critical=False)
        .sign(issuer_key, hashes.SHA256())
    )


def sm2_structure(*, ca=False, direct_oid=False):
    """ASN.1 fixture only; this is not a cryptographically valid SM2 certificate."""
    now = datetime.now(timezone.utc)
    name = asn1_x509.Name.build({'common_name': 'test CA'})
    algorithm = {'algorithm': '1.2.156.10197.1.301'} if direct_oid else {
        'algorithm': 'ec', 'parameters': keys.ECDomainParameters(
            name='named', value='1.2.156.10197.1.301',
        ),
    }
    return Certificate({
        'tbs_certificate': {
            'version': 'v3', 'serial_number': 1 if ca else 2,
            'signature': {'algorithm': '1.2.156.10197.1.501'}, 'issuer': name,
            'validity': {
                'not_before': asn1_x509.Time({'utc_time': now - timedelta(days=1)}),
                'not_after': asn1_x509.Time({'utc_time': now + timedelta(days=1)}),
            },
            'subject': name if ca else asn1_x509.Name.build({'common_name': 'user'}),
            'subject_public_key_info': {
                'algorithm': algorithm, 'public_key': b'\x04' + b'\x01' * 64,
            },
            'extensions': [
                {'extn_id': 'basic_constraints', 'critical': True, 'extn_value': {'ca': ca}},
            ],
        },
        'signature_algorithm': {'algorithm': '1.2.156.10197.1.501'},
        'signature_value': algos.DSASignature({'r': 1, 's': 2}).dump(),
    })


def sm2_p7_structure(certificate, *, gm=False, chain=()):
    return vctk_s.VCTKSContentInfo({
        'content_type': '1.2.156.10197.6.1.4.2.2' if gm else 'signed_data',
        'content': {
            'version': 'v1', 'digest_algorithms': [{'algorithm': vctk_s.SM3_OID}],
            'encap_content_info': {
                'content_type': '1.2.156.10197.6.1.4.2.1' if gm else 'data',
                'content': CHALLENGE.encode(),
            },
            'certificates': [
                vctk_s.VCTKSCertificateChoices(name='certificate', value=item)
                for item in [*chain, certificate]
            ],
            'signer_infos': [{
                'version': 'v1',
                'sid': {'issuer_and_serial_number': {
                    'issuer': certificate.issuer, 'serial_number': certificate.serial_number,
                }},
                'digest_algorithm': {'algorithm': vctk_s.SM3_OID},
                'signature_algorithm': {'algorithm': '1.2.156.10197.1.501'},
                'signature': algos.DSASignature({'r': 1, 's': 2}).dump(),
            }],
        },
    })


class VCTKSVerifierTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.ca = issue_certificate(cls.ca_key, ca=True, name='test CA', serial=1)
        cls.leaf = issue_certificate(cls.key, issuer_key=cls.ca_key, issuer=cls.ca)
        cls.ca_pem = cls.ca.public_bytes(serialization.Encoding.PEM).decode()
        cls.cert = encode(cls.leaf.public_bytes(serialization.Encoding.DER))
        cls.asn1_cert = Certificate.load(cls.leaf.public_bytes(serialization.Encoding.DER))
        cls.p7 = cls.sign_p7(cls.leaf)
        cls.signature = encode(cls.p7)

    @classmethod
    def sign_p7(cls, certificate, message=CHALLENGE, *, attached=True):
        options = [pkcs7.PKCS7Options.Binary]
        if not attached:
            options.append(pkcs7.PKCS7Options.DetachedSignature)
        return (
            pkcs7.PKCS7SignatureBuilder().set_data(message.encode())
            .add_signer(certificate, cls.key, hashes.SHA256()).add_certificate(cls.ca)
            .sign(serialization.Encoding.DER, options)
        )

    def setUp(self):
        self.verifier = vctk_s.VCTKSVerifier(URL)

    def verify_rsa_p7(self, signature, digest_algorithm):
        self.assertEqual(digest_algorithm, 'sha256')
        message = CHALLENGE
        """Independent test double for the remote service's cryptographic check."""
        signer = cms.ContentInfo.load(base64.b64decode(signature))['content']['signer_infos'][0]
        attributes = signer['signed_attrs']
        digest = next(item['values'][0].native for item in attributes
                      if item['type'].native == 'message_digest')
        if digest != hashlib.sha256(message.encode()).digest():
            raise SVSError('Signature mismatch')
        self.key.public_key().verify(
            signer['signature'].native, attributes.untag().dump(),
            padding.PKCS1v15(), hashes.SHA256(),
        )

        return {'plain': CHALLENGE.encode(), 'certificate': self.asn1_cert.dump()}

    def test_real_rsa_p7_with_chain_preserves_existing_identity(self):
        with patch.object(self.verifier, '_client') as client:
            client.return_value.verify_signed_data.side_effect = self.verify_rsa_p7
            claims = self.verifier.verify_proof(self.cert, self.signature, CHALLENGE, 'user')
        self.assertEqual(claims, self.identity())
        client.return_value.verify_signed_data.assert_called_once_with(self.signature, 'sha256')

    def test_config_needs_only_service_settings_and_never_calls_the_service(self):
        self.verifier.validate_config()
        with patch.object(self.verifier, '_client') as client:
            self.verifier.validate_config()
            client.assert_called_once_with()
            client.return_value.verify_signed_data.assert_not_called()
            client.return_value.generate_random.assert_not_called()
        with self.assertRaises(UKeyAuthError) as error:
            vctk_s.VCTKSVerifier('invalid-url').validate_config()
        self.assertNotIn('issuing CA', str(error.exception))

    def test_untrusted_certificate_is_rejected_by_remote_service_without_local_ca(self):
        with patch.object(self.verifier, '_client') as client:
            client.return_value.verify_signed_data.side_effect = SVSError(
                'FF1C0C10: trusted CA certificate validation failed',
            )
            with self.assertRaises(UKeyServiceError):
                self.verifier.verify_proof(self.cert, self.signature, CHALLENGE)
        client.return_value.verify_signed_data.assert_called_once_with(self.signature, 'sha256')

    def test_service_unavailability_cannot_fall_back_to_builtin_verification(self):
        with patch.object(self.verifier, '_client') as client, patch.object(BuiltinVerifier, 'verify_proof') as builtin:
            client.return_value.verify_signed_data.side_effect = OSError('Connection refused')
            with self.assertRaises(UKeyServiceError):
                self.verifier.verify_proof(self.cert, self.signature, CHALLENGE)
            builtin.assert_not_called()

    def test_tampered_attached_signature_is_rejected_by_remote_verification(self):
        content = vctk_s.VCTKSContentInfo.load(self.p7)
        signature = content['content']['signer_infos'][0]['signature'].native
        content['content']['signer_infos'][0]['signature'] = (
            signature[:-1] + bytes([signature[-1] ^ 1])
        )
        with patch.object(self.verifier, '_client') as client:
            client.return_value.verify_signed_data.side_effect = self.verify_rsa_p7
            with self.assertRaises(UKeyServiceError):
                self.verifier.verify_proof(self.cert, encode(content.dump()), CHALLENGE)
        client.return_value.verify_signed_data.assert_called_once()

    def test_explicit_ca_false_preserves_signed_certificate_and_p7_bytes(self):
        leaf = issue_certificate(
            self.key, issuer_key=self.ca_key, issuer=self.ca, explicit_ca_false=True,
        )
        raw = leaf.public_bytes(serialization.Encoding.DER)
        self.assertNotEqual(Certificate.load(raw).dump(force=True), raw)
        certificate = vctk_s.checked_certificate(raw)
        self.assertEqual(certificate.dump(), raw)
        signature = self.sign_p7(leaf)
        parsed = vctk_s.load_signed_der(vctk_s.VCTKSContentInfo, signature)
        self.assertEqual(parsed.dump(), signature)
        with patch.object(self, 'asn1_cert', certificate), patch.object(self.verifier, '_client') as client:
            client.return_value.verify_signed_data.side_effect = self.verify_rsa_p7
            claims = self.verifier.verify_proof(encode(raw), encode(signature), CHALLENGE)
            self.assertEqual(claims, self.identity())
        self.assertEqual(claims['certificate_fingerprint'], hashlib.sha256(raw).hexdigest())
        client.return_value.verify_signed_data.assert_called_once_with(encode(signature), 'sha256')

    def test_explicit_ca_false_does_not_allow_trailing_data_or_signature_substitution(self):
        leaf = issue_certificate(
            self.key, issuer_key=self.ca_key, issuer=self.ca, explicit_ca_false=True,
        )
        raw = leaf.public_bytes(serialization.Encoding.DER)
        signature = self.sign_p7(leaf)
        for cert, proof in ((raw + b'\x00', signature), (raw, signature + b'\x00'),
                            (raw, self.p7)):
            with self.subTest(cert_size=len(cert), signature_size=len(proof)):
                with patch.object(self.verifier, '_client') as client, self.assertRaises(UKeyAuthError):
                    self.verifier.verify_proof(encode(cert), encode(proof), CHALLENGE)
                client.assert_not_called()

    def test_sm2_attached_signer_preserves_explicit_ca_false_for_both_content_oids(self):
        certificate = sm2_structure()
        certificate['tbs_certificate']['extensions'][0]['extn_value'] = asn1_x509.BasicConstraints.load(
            b'\x30\x03\x01\x01\x00',
        )
        raw = certificate.dump()
        parsed = vctk_s.checked_certificate(raw)
        self.assertEqual(parsed.dump(), raw)
        for gm in (False, True):
            with self.subTest(gm=gm):
                signature = sm2_p7_structure(parsed, gm=gm).dump()
                self.assertEqual(vctk_s.check_attached_signer(signature, parsed, CHALLENGE.encode()), 'sm3')
                content = vctk_s.load_signed_der(vctk_s.VCTKSContentInfo, signature)
                self.assertEqual(content.dump(), signature)
                self.assertEqual(content['content']['certificates'][0].chosen.dump(), raw)

    def test_changed_challenge_is_rejected_before_remote_verification(self):
        with patch.object(self.verifier, '_client') as client, self.assertRaises(UKeyAuthError):
            self.verifier.verify_proof(self.cert, self.signature, 'b2' * 32, 'user')
        client.assert_not_called()

    def test_remote_failure_or_returned_content_substitution_cannot_authenticate(self):
        for response in (SVSError('Rejected'),
                         {'plain': b'wrong', 'certificate': self.asn1_cert.dump()},
                         {'plain': CHALLENGE.encode(), 'certificate': b'wrong'}):
            with self.subTest(response=response), patch.object(self.verifier, '_client') as client:
                if isinstance(response, Exception):
                    client.return_value.verify_signed_data.side_effect = response
                else:
                    client.return_value.verify_signed_data.return_value = response
                with self.assertRaises(UKeyServiceError):
                    self.verifier.verify_proof(self.cert, self.signature, CHALLENGE, 'user')
                client.return_value.verify_signed_data.assert_called_once()

    def identity(self):
        cert = self.asn1_cert
        return {
            'certificate_fingerprint': hashlib.sha256(cert.dump()).hexdigest(),
            'issuer_fingerprint': hashlib.sha256(cert.issuer.dump() + (cert.authority_key_identifier or b'')).hexdigest(),
            'serial_number': format(cert.serial_number, 'x'),
        }

    def test_username_is_not_certificate_identity_but_builtin_still_checks_cn(self):
        with patch.object(self.verifier, '_client') as client:
            client.return_value.verify_signed_data.side_effect = self.verify_rsa_p7
            self.assertEqual(self.verifier.verify_proof(self.cert, self.signature, CHALLENGE, 'admin'), self.identity())
            client.return_value.verify_signed_data.assert_called_once()
        with self.assertRaises(UKeyCertCNMismatchError):
            BuiltinVerifier(self.ca_pem).verify_certificate(self.cert, 'admin')

    def test_valid_issuer_metadata_still_requires_cryptographic_certificate_signature(self):
        tampered = self.asn1_cert.copy()
        tampered['signature_value'] = b'\x00' * 256
        with self.assertRaises(UKeyCertChainError):
            BuiltinVerifier(self.ca_pem).verify_certificate(encode(tampered.dump()), 'user')

    def test_expired_future_or_ca_leaf_are_rejected_before_remote_verification(self):
        for kwargs in ({'start': -2, 'end': -1}, {'start': 1, 'end': 2}, {'ca': True}):
            leaf = issue_certificate(self.key, issuer_key=self.ca_key, issuer=self.ca, **kwargs)
            with self.subTest(kwargs=kwargs), patch.object(self.verifier, '_client') as client:
                with self.assertRaises(UKeyAuthError):
                    self.verifier.verify_proof(
                        encode(leaf.public_bytes(serialization.Encoding.DER)),
                        encode(self.sign_p7(leaf)), CHALLENGE, 'user',
                    )
                client.assert_not_called()

    def test_malformed_challenges_signatures_and_oversized_inputs_fail_locally(self):
        for cert, signature, challenge in (
            (self.cert, self.signature, CHALLENGE.upper()),
            (self.cert, self.signature, CHALLENGE * 2),
            (self.cert, self.signature, encode(CHALLENGE.encode())),
            ('invalid!', self.signature, CHALLENGE),
            (self.cert, '', CHALLENGE),
            (self.cert, encode(b'x' * (MAX_P7_SIZE + 1)), CHALLENGE),
            (self.cert, encode(self.p7 + b'\x00'), CHALLENGE),
        ):
            with self.subTest(challenge=challenge), patch.object(self.verifier, '_client') as client:
                with self.assertRaises(UKeyAuthError):
                    self.verifier.verify_proof(cert, signature, challenge, 'user')
                client.assert_not_called()

    def test_substituting_submitted_certificate_cannot_use_another_p7_signer(self):
        other = issue_certificate(self.key, issuer_key=self.ca_key, issuer=self.ca, serial=456)
        with self.assertRaises(ValueError):
            vctk_s.check_attached_signer(
                self.p7, Certificate.load(other.public_bytes(serialization.Encoding.DER)), CHALLENGE.encode(),
            )

    def test_attached_signer_requires_one_unambiguous_matching_certificate(self):
        for kind in ('wrong_sid', 'multiple_signers', 'missing_signer', 'missing_certificates',
                     'duplicate_signing_certificate', 'wrong_digest', 'empty_signature'):
            content = vctk_s.VCTKSContentInfo.load(self.p7)
            signed = content['content']
            if kind == 'wrong_sid':
                signed['signer_infos'][0]['sid'].chosen['serial_number'] = 456
            elif kind == 'multiple_signers':
                signed['signer_infos'].append(signed['signer_infos'][0].copy())
            elif kind == 'missing_signer':
                signed['signer_infos'] = []
            elif kind == 'missing_certificates':
                signed['certificates'] = None
            elif kind == 'duplicate_signing_certificate':
                signed['certificates'].append(
                    vctk_s.VCTKSCertificateChoices(name='certificate', value=self.asn1_cert),
                )
            elif kind == 'wrong_digest':
                signed['signer_infos'][0]['digest_algorithm']['algorithm'] = 'sha1'
            else:
                signed['signer_infos'][0]['signature'] = b''
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                vctk_s.check_attached_signer(content.dump(force=True), self.asn1_cert, CHALLENGE.encode())

    def test_detached_raw_or_truncated_vendor_example_is_rejected(self):
        for data in (
            self.sign_p7(self.leaf, attached=False),
            self.key.sign(CHALLENGE.encode(), padding.PKCS1v15(), hashes.SHA256()),
            base64.b64decode('MIIDUQYKKoEcz1UGAQQCAqCCA0EwggM9gECAghUh=='),
        ):
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                vctk_s.check_attached_signer(data, self.asn1_cert, CHALLENGE.encode())

    def test_subject_key_identifier_signer_is_resolved(self):
        content = vctk_s.VCTKSContentInfo.load(self.p7)
        content['content']['version'] = 'v3'
        signer = content['content']['signer_infos'][0]
        signer['version'] = 'v3'
        signer['sid'] = {'subject_key_identifier': self.asn1_cert.key_identifier}
        vctk_s.check_attached_signer(content.dump(force=True), self.asn1_cert, CHALLENGE.encode())
        signer['sid'] = {'subject_key_identifier': b'wrong'}
        with self.assertRaises(ValueError):
            vctk_s.check_attached_signer(content.dump(force=True), self.asn1_cert, CHALLENGE.encode())

    def test_connection_test_only_checks_random_generation(self):
        with patch.object(self.verifier, '_client') as client:
            result = self.verifier.test_connection()
        client.return_value.generate_random.assert_called_once_with()
        client.return_value.verify_signed_data.assert_not_called()
        self.assertTrue(result['connection'])
        self.assertFalse(result['verification'])
        self.assertIn('not been tested', str(result['msg']))

    def test_builtin_rsa_signature_flow_is_unchanged(self):
        verifier = BuiltinVerifier(self.ca_pem)
        signature = encode(self.key.sign(CHALLENGE.encode(), padding.PKCS1v15(), hashes.SHA256()))
        self.assertEqual(
            verifier.verify_proof(self.cert, signature, CHALLENGE, 'user'),
            {'subject_cn': 'user'},
        )
        with self.assertRaises(UKeySignatureError):
            verifier.verify_proof(self.cert, signature, 'b2' * 16, 'user')


class VCTKSSM2StructureTests(TestCase):
    def test_standard_and_gm_envelopes_accept_sm2_curve_and_direct_key_oids(self):
        for gm in (False, True):
            for direct_oid in (False, True):
                leaf = sm2_structure(direct_oid=direct_oid)
                ca = sm2_structure(ca=True, direct_oid=direct_oid)
                with self.subTest(gm=gm, direct_oid=direct_oid):
                    vctk_s.check_attached_signer(
                        sm2_p7_structure(leaf, gm=gm, chain=(ca,)).dump(), leaf, CHALLENGE.encode(),
                    )
                    self.assertEqual(vctk_s.certificate_algorithm(vctk_s.checked_certificate(leaf.dump())), 'sm2')

    def test_shared_sm2_checks_keep_chain_validity_and_cn_before_signature(self):
        verifier = BuiltinVerifier('test CA')
        native_cert = MagicMock()
        native_cert.get_subject.return_value = {'commonName': 'user'}
        with patch.object(verifier, '_load_cert_pem', return_value='cert'), \
                patch.object(verifier, '_is_sm2_cert', return_value=True), \
                patch.object(verifier, '_load_sm2_cert', return_value=native_cert), \
                patch.object(verifier, '_verify_sm2_cert_chain') as chain, \
                patch.object(verifier, '_verify_sm2_cert_validity') as validity, \
                patch.object(verifier, '_verify_sm2_signature') as signature:
            self.assertEqual(verifier.verify_certificate('cert', 'user'), {'subject_cn': 'user'})
            chain.assert_called_once_with(native_cert)
            validity.assert_called_once_with(native_cert)
            signature.assert_not_called()
            verifier.verify_proof('cert', 'signature', CHALLENGE, 'user')
            signature.assert_called_once_with(
                native_cert.get_subject_public_key(), 'signature', CHALLENGE,
            )
            with self.assertRaises(UKeyCertCNMismatchError):
                verifier.verify_certificate('cert', 'other')
