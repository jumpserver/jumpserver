"""Real GmSSL certificate and signature checks; no device or HTTP service needed."""
import base64
import hashlib
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import TestCase, skipUnless
from unittest.mock import patch

from asn1crypto import pem

from authentication.backends.ukey.exceptions import UKeyCertChainError, UKeyCertCNMismatchError
from authentication.backends.ukey.verifiers import vctk_s
from authentication.backends.ukey.verifiers.builtin import BuiltinVerifier


@skipUnless(shutil.which('gmssl'), 'Requires the deployed GmSSL executable and library')
class VCTKSRealSM2Tests(TestCase):
    @classmethod
    def setUpClass(cls):
        from common.utils.gmssl_python import Sm2Key, Sm2Signature, DO_SIGN, SM2_DEFAULT_ID

        temporary = tempfile.TemporaryDirectory(prefix='vctks-sm2-test-')
        cls.addClassCleanup(temporary.cleanup)
        cls.directory = Path(temporary.name)
        cls.challenge = 'ab' * 32

        def gmssl(*args):
            subprocess.run(
                ['gmssl', *args], cwd=cls.directory, check=True, timeout=20,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )

        for name, cn in [('root', 'Root'), ('issuer', 'Issuer'), ('wrong', 'Issuer'), ('user', 'user')]:
            gmssl('sm2keygen', '-pass', 'test-only', '-out', name + '.key')
            if name in ('root', 'wrong'):
                gmssl('certgen', '-CN', cn, '-key', name + '.key', '-pass', 'test-only',
                      '-days', '1' if name == 'wrong' else '3',
                      '-ca', '-key_usage', 'keyCertSign', '-out', name + '.pem')
            else:
                gmssl('reqgen', '-CN', cn, '-key', name + '.key', '-pass', 'test-only',
                      '-out', name + '.csr')
                issuer = 'root' if name == 'issuer' else 'issuer'
                extensions = ['-ca', '-key_usage', 'keyCertSign'] if name == 'issuer' else [
                    '-key_usage', 'digitalSignature',
                ]
                gmssl('reqsign', '-in', name + '.csr', '-cacert', issuer + '.pem',
                      '-key', issuer + '.key', '-pass', 'test-only', '-days', '2',
                      '-serial_len', '12', *extensions, '-out', name + '.pem')
        cls.root_pem = (cls.directory / 'root.pem').read_text()
        cls.issuer_pem = (cls.directory / 'issuer.pem').read_text()
        cls.wrong_pem = (cls.directory / 'wrong.pem').read_text()
        cls.cert_pem = (cls.directory / 'user.pem').read_text()
        cls.cert_der = pem.unarmor(cls.cert_pem.encode())[2]
        cls.cert = base64.b64encode(cls.cert_der).decode()
        certificate = vctk_s.checked_certificate(cls.cert_der)
        key = Sm2Key()
        key.import_encrypted_private_key_info_pem(str(cls.directory / 'user.key'), 'test-only')
        signer = Sm2Signature(key, SM2_DEFAULT_ID, DO_SIGN)
        signer.update(cls.challenge.encode())
        cls.signature = base64.b64encode(vctk_s.VCTKSContentInfo({
            'content_type': 'signed_data',
            'content': {
                'version': 'v1', 'digest_algorithms': [{'algorithm': vctk_s.SM3_OID}],
                'encap_content_info': {'content_type': 'data', 'content': cls.challenge.encode()},
                'certificates': [
                    vctk_s.VCTKSCertificateChoices(name='certificate', value=certificate),
                ],
                'signer_infos': [{
                    'version': 'v1',
                    'sid': {'issuer_and_serial_number': {
                        'issuer': certificate.issuer, 'serial_number': certificate.serial_number,
                    }},
                    'digest_algorithm': {'algorithm': vctk_s.SM3_OID},
                    'signature_algorithm': {'algorithm': '1.2.156.10197.1.501'},
                    'signature': signer.sign(),
                }],
            },
        }).dump()).decode()

    def verify_remote_result(self, signature, digest):
        from common.utils.gmssl_python import Sm2Signature, DO_VERIFY, SM2_DEFAULT_ID

        self.assertEqual(digest, 'sm3')
        signed = vctk_s.VCTKSContentInfo.load(base64.b64decode(signature))['content']
        key = BuiltinVerifier._load_sm2_cert(self.cert_pem).get_subject_public_key()
        verifier = Sm2Signature(key, SM2_DEFAULT_ID, DO_VERIFY)
        verifier.update(signed['encap_content_info']['content'].native)
        self.assertTrue(verifier.verify(signed['signer_infos'][0]['signature'].native))
        return {'plain': self.challenge.encode(), 'certificate': self.cert_der}

    def test_real_sm2_bundle_order_and_wrong_same_name_key(self):
        for bundle in (self.root_pem + self.issuer_pem, self.issuer_pem + self.root_pem,
                       self.wrong_pem + self.root_pem + self.issuer_pem):
            with self.subTest(first=bundle[:80]):
                verifier = vctk_s.VCTKSVerifier('http://192.0.2.1', issuing_ca=bundle)
                verifier.validate_config()
                with patch.object(verifier, '_client') as client:
                    client.return_value.verify_signed_data.side_effect = self.verify_remote_result
                    self.assertEqual(verifier.verify_proof(
                        self.cert, self.signature, self.challenge, 'user'
                    ), self.identity())
                    client.return_value.verify_signed_data.assert_called_once()

    def test_real_sm2_wrong_ca_and_missing_direct_issuer_fail(self):
        for bundle in (self.wrong_pem, self.root_pem):
            verifier = vctk_s.VCTKSVerifier(issuing_ca=bundle)
            with patch.object(verifier, '_client') as client, self.assertRaises(UKeyCertChainError):
                verifier.verify_proof(self.cert, self.signature, self.challenge, 'user')
            client.assert_not_called()

    def identity(self):
        cert = vctk_s.checked_certificate(self.cert_der)
        return {
            'certificate_fingerprint': hashlib.sha256(self.cert_der).hexdigest(),
            'issuer_fingerprint': hashlib.sha256(cert.issuer.dump() + (cert.authority_key_identifier or b'')).hexdigest(),
            'serial_number': format(cert.serial_number, 'x'),
        }

    def test_real_sm2_cn_is_display_only_but_builtin_still_requires_match(self):
        verifier = vctk_s.VCTKSVerifier(issuing_ca=self.issuer_pem + self.root_pem)
        with patch.object(verifier, '_client') as client:
            client.return_value.verify_signed_data.side_effect = self.verify_remote_result
            self.assertEqual(verifier.verify_proof(self.cert, self.signature, self.challenge, 'admin'), self.identity())
        with self.assertRaises(UKeyCertCNMismatchError):
            BuiltinVerifier(self.issuer_pem).verify_certificate(self.cert, 'admin')

    def test_real_sm2_unused_ca_expiry_does_not_block_login(self):
        verifier = vctk_s.VCTKSVerifier(issuing_ca=self.wrong_pem + self.issuer_pem)
        # Only the unused one-day CA has expired at this instant.
        future = datetime.now(timezone.utc) + timedelta(days=1, hours=1)
        with patch.object(vctk_s, 'datetime') as clock, patch.object(verifier, '_client') as client:
            clock.now.return_value = future
            client.return_value.verify_signed_data.side_effect = self.verify_remote_result
            self.assertEqual(verifier.verify_proof(
                self.cert, self.signature, self.challenge, 'user'
            ), self.identity())

    def test_real_sm2_and_rsa_cas_can_share_one_file(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from authentication.tests.test_ukey_vctk_s_verifier import issue_certificate

        rsa_ca = issue_certificate(
            rsa.generate_private_key(public_exponent=65537, key_size=2048), ca=True, name='RSA CA'
        ).public_bytes(serialization.Encoding.PEM).decode()
        verifier = vctk_s.VCTKSVerifier(issuing_ca=rsa_ca + self.issuer_pem)
        with patch.object(verifier, '_client') as client:
            client.return_value.verify_signed_data.side_effect = self.verify_remote_result
            self.assertEqual(verifier.verify_proof(
                self.cert, self.signature, self.challenge, 'user'
            ), self.identity())
