"""P7 signer binding and real RSA certificate checks, without vendor hardware."""
import base64
import hashlib
from datetime import datetime, timedelta, timezone
from unittest import TestCase
from unittest.mock import MagicMock, patch

from asn1crypto import algos, cms, keys, pem, x509 as asn1_x509
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
                      serial=123, start=-1, end=1):
    now = datetime.now(timezone.utc)
    subject = x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, name)])
    issuer_key = issuer_key or key
    return (
        x509.CertificateBuilder().subject_name(subject).issuer_name(issuer.subject if issuer else subject)
        .serial_number(serial).public_key(key.public_key())
        .not_valid_before(now + timedelta(days=start)).not_valid_after(now + timedelta(days=end))
        .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
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
        self.verifier = vctk_s.VCTKSVerifier(URL, issuing_ca=self.ca_pem)

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

    def test_wrong_issuing_key_is_rejected_before_remote_verification(self):
        wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        wrong_ca = issue_certificate(wrong_key, ca=True, name='test CA', serial=1)
        # The genuine CA name alone must not establish trust.
        verifier = vctk_s.VCTKSVerifier(
            URL, issuing_ca=wrong_ca.public_bytes(serialization.Encoding.PEM).decode(),
        )
        with patch.object(verifier, '_client') as client, self.assertRaises(UKeyAuthError):
            verifier.verify_proof(self.cert, self.signature, CHALLENGE, 'user')
        client.assert_not_called()

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

    def test_config_accepts_ca_bundles_but_not_leaf_or_only_expired_ca(self):
        self.verifier.validate_config()
        self.assertEqual(vctk_s.certificate_algorithm(vctk_s.load_issuing_cas(self.ca_pem)[0]), 'rsa')
        self.assertEqual(len(vctk_s.load_issuing_cas(self.ca_pem * 2)), 1)
        expired = issue_certificate(self.ca_key, ca=True, name='test CA', start=-2, end=-1)
        for value in ('', self.leaf.public_bytes(serialization.Encoding.PEM).decode(),
                      expired.public_bytes(serialization.Encoding.PEM).decode()):
            with self.subTest(size=len(value)), self.assertRaises(vctk_s.VCTKSCAConfigError):
                vctk_s.VCTKSVerifier(URL, issuing_ca=value).validate_config()

    def test_multi_ca_order_and_unused_expired_ca_do_not_affect_login(self):
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        for dates in ({}, {'start': -2, 'end': -1}, {'start': 1, 'end': 2}):
            other = issue_certificate(other_key, ca=True, name='other CA', **dates)
            other_pem = other.public_bytes(serialization.Encoding.PEM).decode()
            for bundle in (other_pem + self.ca_pem, self.ca_pem + other_pem):
                with self.subTest(dates=dates, first_is_other=bundle.startswith(other_pem)):
                    verifier = vctk_s.VCTKSVerifier(URL, issuing_ca=bundle)
                    verifier.validate_config()
                    with patch.object(verifier, '_client') as client:
                        client.return_value.verify_signed_data.side_effect = self.verify_rsa_p7
                        self.assertEqual(verifier.verify_proof(
                            self.cert, self.signature, CHALLENGE, 'user'
                        ), self.identity())

    def test_same_name_wrong_key_candidate_does_not_hide_valid_issuer(self):
        wrong_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        wrong_ca = Certificate.load(issue_certificate(
            wrong_key, ca=True, name='test CA'
        ).public_bytes(serialization.Encoding.DER))
        # Make issuer metadata match too: only a real signature check distinguishes it.
        for extension in wrong_ca['tbs_certificate']['extensions']:
            if extension['extn_id'].native == 'key_identifier':
                extension['extn_value'] = self.asn1_cert.authority_key_identifier
        wrong_pem = pem.armor('CERTIFICATE', wrong_ca.dump()).decode()
        verifier = vctk_s.VCTKSVerifier(URL, issuing_ca=wrong_pem + self.ca_pem)
        self.assertEqual(len(vctk_s.load_issuing_cas(verifier.issuing_ca)), 2)
        with patch.object(verifier, '_client') as client:
            client.return_value.verify_signed_data.side_effect = self.verify_rsa_p7
            self.assertEqual(verifier.verify_proof(
                self.cert, self.signature, CHALLENGE, 'user'
            ), self.identity())

    def test_expired_matching_ca_cannot_be_replaced_by_unrelated_valid_ca(self):
        expired = issue_certificate(self.ca_key, ca=True, name='test CA', start=-2, end=-1)
        unrelated = issue_certificate(self.ca_key, ca=True, name='unrelated CA')
        bundle = ''.join(c.public_bytes(serialization.Encoding.PEM).decode() for c in (expired, unrelated))
        verifier = vctk_s.VCTKSVerifier(URL, issuing_ca=bundle)
        with patch.object(verifier, '_client') as client, self.assertRaises(UKeyCertChainError):
            verifier.verify_proof(self.cert, self.signature, CHALLENGE, 'user')
        client.assert_not_called()

    def test_uploaded_root_does_not_implicitly_trust_a_p7_intermediate(self):
        root_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        root = issue_certificate(root_key, ca=True, name='root')
        intermediate = issue_certificate(self.ca_key, issuer_key=root_key, issuer=root, ca=True, name='test CA')
        signature = (
            pkcs7.PKCS7SignatureBuilder().set_data(CHALLENGE.encode())
            .add_signer(self.leaf, self.key, hashes.SHA256()).add_certificate(intermediate)
            .sign(serialization.Encoding.DER, [pkcs7.PKCS7Options.Binary])
        )
        verifier = vctk_s.VCTKSVerifier(URL, issuing_ca=root.public_bytes(serialization.Encoding.PEM).decode())
        with patch.object(verifier, '_client') as client, self.assertRaises(UKeyCertChainError):
            verifier.verify_proof(self.cert, encode(signature), CHALLENGE, 'user')
        client.assert_not_called()

    def test_bundle_rejects_garbage_and_limits_certificate_count_and_size(self):
        for value in ('garbage' + self.ca_pem, self.ca_pem + 'garbage',
                      self.ca_pem + '-----BEGIN CERTIFICATE-----broken',
                      self.ca_pem + '-----BEGIN PUBLIC KEY-----\nAA==\n-----END PUBLIC KEY-----',
                      self.ca_pem * 17, self.ca_pem + ' ' * vctk_s.MAX_CA_BUNDLE_SIZE,
                      '\ud800' + self.ca_pem,
                      '-----BEGIN CERTIFICATE-----\n'
                      + encode(b'\x00' * (vctk_s.MAX_CERT + 1))
                      + '\n-----END CERTIFICATE-----'):
            with self.subTest(size=len(value)), self.assertRaises(vctk_s.VCTKSCAConfigError):
                vctk_s.load_issuing_cas(value)

    def test_bad_certificate_reports_its_position_without_echoing_contents(self):
        with self.assertRaises(vctk_s.VCTKSCAConfigError) as error:
            vctk_s.load_issuing_cas(
                self.ca_pem + self.leaf.public_bytes(serialization.Encoding.PEM).decode()
            )
        self.assertIn('2:', str(error.exception))
        self.assertNotIn('BEGIN CERTIFICATE', str(error.exception))

    def test_mixed_rsa_sm2_bundle_does_not_change_rsa_proof(self):
        sm2_ca = pem.armor('CERTIFICATE', sm2_structure(ca=True).dump()).decode()
        verifier = vctk_s.VCTKSVerifier(URL, issuing_ca=sm2_ca + self.ca_pem)
        verifier.validate_config()
        with patch.object(verifier, '_client') as client:
            client.return_value.verify_signed_data.side_effect = self.verify_rsa_p7
            self.assertEqual(verifier.verify_proof(
                self.cert, self.signature, CHALLENGE, 'user'
            ), self.identity())

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
                    loaded = vctk_s.load_issuing_cas(pem.armor('CERTIFICATE', ca.dump()).decode())[0]
                    self.assertEqual(vctk_s.certificate_algorithm(loaded), 'sm2')

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
