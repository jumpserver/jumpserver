import base64
import json
import os
import shutil
import subprocess
import tempfile
from datetime import timedelta
from pathlib import Path
from struct import unpack
from types import SimpleNamespace
from unittest.mock import Mock, patch

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from django.test import SimpleTestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIRequestFactory
from rest_framework.viewsets import ViewSet

from authentication.api.connection_token import (
    ExtraActionApiMixin, RDPFileClientProtocolURLMixin, RDPFileSigningError, logger,
)
from common.exceptions import JMSException
from terminal.connect_methods import NativeClient


CONTENT = (
    'full address:s:rdp.example.test:3389\n'
    'username:s:test-user\n'
    'authentication level:i:2\n'
    'remoteapplicationname:s:测试应用\n'
    'redirectwebauthn:i:1\n'
)
SCOPE = (
    'Full Address,Alternate Full Address,RemoteApplicationName,'
    'Authentication Level,RedirectWebAuthn'
)
SIGNED_MESSAGE = (
    'full address:s:rdp.example.test:3389\r\n'
    'alternate full address:s:rdp.example.test:3389\r\n'
    'remoteapplicationname:s:测试应用\r\n'
    'authentication level:i:2\r\n'
    'redirectwebauthn:i:1\r\n'
    f'signscope:s:{SCOPE}\r\n\x00'
)


class RDPFileTestViewSet(ExtraActionApiMixin, ViewSet):
    authentication_classes = ()
    permission_classes = ()
    throttle_classes = ()
    token = None

    def get_object(self):
        return self.token


@override_settings(
    RDP_SIGN_ENABLED=True,
    RDP_SIGN_CERT='rdp_signer.crt',
    RDP_SIGN_CERT_KEY='rdp_signer.key',
)
class RDPFileSigningTests(SimpleTestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.enterContext(self.settings(PROJECT_DIR=str(self.directory)))
        cert_dir = self.directory / 'data' / 'certs'
        cert_dir.mkdir(parents=True)
        self.certfile = cert_dir / 'rdp_signer.crt'
        self.keyfile = cert_dir / 'rdp_signer.key'
        self.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.write_certificate()
        self.write_private_key(self.private_key)

    def write_certificate(self, valid_from=None, valid_to=None, usage=ExtendedKeyUsageOID.CODE_SIGNING):
        now = timezone.now()
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'RDP test signer')])
        builder = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(subject)
            .public_key(self.private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(valid_from if valid_from is not None else now - timedelta(days=1))
            .not_valid_after(valid_to if valid_to is not None else now + timedelta(days=1))
        )
        if usage is not None:
            builder = builder.add_extension(x509.ExtendedKeyUsage([usage]), critical=False)
        certificate = builder.sign(self.private_key, hashes.SHA256())
        self.certfile.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))

    def write_private_key(self, private_key, encryption=None):
        self.keyfile.write_bytes(private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            encryption if encryption is not None else serialization.NoEncryption(),
        ))
        self.keyfile.chmod(0o600)

    def sign(self, content=CONTENT):
        return RDPFileClientProtocolURLMixin._try_sign_rdp_content(content)

    def verify_signature(self, signed_content, message):
        openssl = shutil.which('openssl')
        if not openssl:
            self.skipTest('OpenSSL is required for independent PKCS#7 verification')
        encoded = next(
            line[len('signature:s:'):]
            for line in signed_content.splitlines() if line.startswith('signature:s:')
        )
        signature_blob = base64.b64decode(encoded, validate=True)
        version, count, length = unpack('<III', signature_blob[:12])
        self.assertEqual((version, count, length), (0x00010001, 1, len(signature_blob) - 12))
        signature_file = self.directory / 'signature.der'
        message_file = self.directory / 'message.bin'
        signature_file.write_bytes(signature_blob[12:])
        message_file.write_bytes(message.encode('UTF-16LE'))
        result = subprocess.run([
            openssl, 'cms', '-verify', '-binary', '-inform', 'DER',
            '-in', str(signature_file), '-content', str(message_file),
            '-noverify', '-out', os.devnull,
        ], capture_output=True, timeout=10)
        return result.returncode == 0

    def test_disabled_signing_preserves_exact_content_without_reading_files(self):
        content = '\r\n' + CONTENT.replace('\n', '\r\n') + 'signature:s:old\r\n'
        with self.settings(RDP_SIGN_ENABLED=False), patch('builtins.open') as open_file:
            self.assertEqual(self.sign(content), content)
            open_file.assert_not_called()

    def test_signature_covers_expected_fields_and_unicode_values(self):
        signed = self.sign()
        self.assertIn(f'signscope:s:{SCOPE}\r\n', signed)
        self.assertIn('alternate full address:s:rdp.example.test:3389\r\n', signed)
        self.assertTrue(self.verify_signature(signed, SIGNED_MESSAGE))

    def test_tampering_with_protected_fields_invalidates_signature(self):
        signed = self.sign()
        for original, replacement in (
            ('rdp.example.test:3389', 'other.example.test:3389'),
            ('authentication level:i:2', 'authentication level:i:0'),
            ('remoteapplicationname:s:测试应用', 'remoteapplicationname:s:other'),
            ('redirectwebauthn:i:1', 'redirectwebauthn:i:0'),
        ):
            with self.subTest(field=original):
                self.assertFalse(self.verify_signature(
                    signed, SIGNED_MESSAGE.replace(original, replacement),
                ))

    def test_resigning_replaces_metadata_and_normalizes_line_endings(self):
        original = self.sign()
        for content in (original, original.replace('\r\n', '\n')):
            with self.subTest(crlf='\r\n' in content):
                signed = self.sign(content)
                self.assertEqual(signed.count('signature:s:'), 1)
                self.assertEqual(signed.count('signscope:s:'), 1)
                self.assertNotIn('\n', signed.replace('\r\n', ''))
                self.assertEqual(signed.count('alternate full address:s:'), 1)

    def test_missing_certificate_or_key_fails_closed(self):
        for path in (self.certfile, self.keyfile):
            with self.subTest(filename=path.name):
                original = path.read_bytes()
                path.unlink()
                try:
                    with self.assertRaises(RDPFileSigningError):
                        self.sign()
                finally:
                    path.write_bytes(original)
                    if path == self.keyfile:
                        path.chmod(0o600)

    def test_malformed_certificate_or_key_fails_closed(self):
        for path in (self.certfile, self.keyfile):
            with self.subTest(filename=path.name):
                original = path.read_bytes()
                path.write_bytes(b'not a PEM file')
                try:
                    with self.assertRaises(RDPFileSigningError):
                        self.sign()
                finally:
                    path.write_bytes(original)

    def test_encrypted_and_mismatched_private_keys_fail_closed(self):
        self.write_private_key(self.private_key, serialization.BestAvailableEncryption(b'test-only'))
        with self.assertRaises(RDPFileSigningError):
            self.sign()
        self.write_private_key(rsa.generate_private_key(public_exponent=65537, key_size=2048))
        with self.assertRaises(RDPFileSigningError):
            self.sign()

    def test_certificate_dates_and_code_signing_usage_are_required(self):
        now = timezone.now()
        for options in (
            {'valid_from': now - timedelta(days=2), 'valid_to': now - timedelta(days=1)},
            {'valid_from': now + timedelta(days=1), 'valid_to': now + timedelta(days=2)},
            {'usage': ExtendedKeyUsageOID.SERVER_AUTH},
            {'usage': None},
        ):
            with self.subTest(options=options):
                self.write_certificate(**options)
                with self.assertRaises(RDPFileSigningError):
                    self.sign()

    def test_unsigned_content_is_not_returned_when_no_fields_can_be_signed(self):
        with self.assertRaises(RDPFileSigningError):
            self.sign('username:s:test-user\n')

    def test_io_and_signing_errors_do_not_expose_content_or_paths(self):
        sensitive = 'sensitive-path-or-key-content'
        for target in ('builtins.open', 'authentication.api.connection_token.pkcs7.PKCS7SignatureBuilder'):
            with self.subTest(target=target), patch(target, side_effect=OSError(sensitive)):
                with self.assertLogs(logger.name, level='ERROR') as logs:
                    with self.assertRaises(RDPFileSigningError) as failure:
                        self.sign()
                self.assertEqual(failure.exception.status_code, 503)
                self.assertEqual(failure.exception.get_codes(), 'rdp_signing_failed')
                output = ' '.join(logs.output) + str(failure.exception.detail)
                self.assertNotIn(sensitive, output)
                self.assertNotIn(str(self.directory), output)
                self.assertNotIn('test-user', output)

    def make_token(self):
        protocols = Mock()
        protocols.filter.return_value.first.return_value = None
        return SimpleNamespace(
            id='test-token-id', value='test-token-value', account='test-user', input_username='',
            connect_method=NativeClient.mstsc, protocol='rdp', connect_options={},
            user=SimpleNamespace(username='test-user'),
            asset=SimpleNamespace(name='test-asset', platform=SimpleNamespace(protocols=protocols)),
            is_valid=Mock(), set_reusable=Mock(), date_expired=timezone.now(),
            get_remote_app_option=Mock(return_value={
                'remoteapplicationmode:i': '1', 'remoteapplicationprogram:s': '||test-app',
            }),
        )

    def request_action(self, action, token, query=None, method_type='native'):
        view = RDPFileTestViewSet.as_view({'get': action}, token=token)
        request = APIRequestFactory().get('/connection-token/', data=query or {})
        endpoint = SimpleNamespace(host='rdp.example.test', rdp_port=3389)
        with patch.object(RDPFileTestViewSet, 'get_smart_endpoint', return_value=endpoint), patch(
            'authentication.api.connection_token.get_request_os', return_value='Windows',
        ), patch(
            'authentication.api.connection_token.ConnectMethodUtil.get_connect_method',
            return_value={'type': method_type},
        ):
            return view(request)

    def test_download_and_client_url_both_contain_signed_rdp(self):
        token = self.make_token()
        download = self.request_action('get_rdp_file', token, {'reusable': '1'})
        self.assertEqual(download.status_code, 200)
        self.assertIn(b'signature:s:', download.content)
        self.assertIn(token.date_expired.strftime('%Y%m%d_%H%M%S'), download['Content-Disposition'])
        token.set_reusable.assert_called_once_with(True)
        response = self.request_action('get_client_protocol_url', token)
        self.assertEqual(response.status_code, 200)
        data = json.loads(base64.b64decode(response.data['url'][len('jms://'):]))
        self.assertEqual(data['protocol'], 'rdp')
        self.assertIn('signature:s:', data['file']['content'])

    def test_both_endpoints_fail_closed_without_returning_rdp_or_client_url(self):
        self.keyfile.unlink()
        for action in ('get_rdp_file', 'get_client_protocol_url'):
            with self.subTest(action=action):
                response = self.request_action(action, self.make_token(), {'reusable': '1'})
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.data['code'], 'rdp_signing_failed')
                self.assertEqual(set(response.data), {'code', 'detail'})
                self.assertNotIn(str(self.directory), str(response.data))

    def test_applet_client_url_uses_the_same_signing_and_failure_policy(self):
        token = self.make_token()
        token.connect_method = 'test-applet'
        response = self.request_action('get_client_protocol_url', token, method_type='applet')
        self.assertEqual(response.status_code, 200)
        data = json.loads(base64.b64decode(response.data['url'][len('jms://'):]))
        self.assertIn('RemoteApplicationProgram', data['file']['content'])
        self.keyfile.unlink()
        response = self.request_action('get_client_protocol_url', token, method_type='applet')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data['code'], 'rdp_signing_failed')

    def test_invalid_token_is_rejected_before_signing(self):
        token = self.make_token()
        token.is_valid.side_effect = JMSException('Invalid test token')
        for action in ('get_rdp_file', 'get_client_protocol_url'):
            with self.subTest(action=action), patch.object(
                RDPFileClientProtocolURLMixin, '_try_sign_rdp_content',
            ) as sign:
                response = self.request_action(action, token)
                self.assertEqual(response.status_code, 400)
                sign.assert_not_called()
