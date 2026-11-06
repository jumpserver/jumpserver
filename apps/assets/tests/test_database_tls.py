from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID
from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from assets.models import Database
from assets.serializers.asset.database import DatabaseSerializer
from assets.serializers.asset.info.spec import DatabaseSpecSerializer


class DatabaseTLSTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        key = ec.generate_private_key(ec.SECP256R1())
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'database-tls-test')])
        now = datetime.now(timezone.utc)
        cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
                .public_key(key.public_key()).serial_number(1)
                .not_valid_before(now - timedelta(hours=1)).not_valid_after(now + timedelta(hours=1))
                .sign(key, hashes.SHA256()))
        cls.cert = cert.public_bytes(serialization.Encoding.PEM).decode()
        cls.key = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                    serialization.NoEncryption()).decode()

    def validate(self, attrs, protocol='postgresql', instance=None):
        serializer = DatabaseSerializer.__new__(DatabaseSerializer)
        serializer.instance = instance
        serializer.get_platform = lambda: SimpleNamespace(type=protocol)
        return serializer.validate(attrs)

    def test_component_spec_includes_the_actual_postgres_mode(self):
        asset = Database(db_name='app', use_ssl=True, pg_ssl_mode='verify-ca')
        self.assertEqual(DatabaseSpecSerializer(asset).data['pg_ssl_mode'], 'verify-ca')

    def test_newly_enabled_postgres_uses_verified_identity_without_overwriting_existing_modes(self):
        self.assertEqual(self.validate({'use_ssl': True})['pg_ssl_mode'], 'verify-full')
        instance = SimpleNamespace(use_ssl=True, pg_ssl_mode='require')
        self.assertNotIn('pg_ssl_mode', self.validate({'ca_cert': self.cert}, instance=instance))
        self.assertEqual(self.validate({'use_ssl': True, 'pg_ssl_mode': 'prefer'})['pg_ssl_mode'], 'prefer')

    def test_valid_mutual_tls_pair_is_preserved(self):
        for protocol in ('mysql', 'mariadb', 'postgresql'):
            attrs = {'use_ssl': True, 'ca_cert': self.cert, 'client_cert': self.cert, 'client_key': self.key}
            result = self.validate(attrs, protocol)
            self.assertEqual(result['client_key'], self.key)

    def test_invalid_or_incomplete_pem_is_rejected_without_echoing_secrets(self):
        for attrs, field in (
            ({'client_key': 'private-key-sentinel'}, 'client_cert'),
            ({'client_cert': self.cert}, 'client_key'),
            ({'ca_cert': 'private-key-sentinel'}, 'ca_cert'),
            ({'client_cert': self.cert, 'client_key': 'private-key-sentinel'}, 'client_key'),
        ):
            with self.assertRaises(ValidationError) as caught:
                self.validate({'use_ssl': True, **attrs})
            self.assertIn(field, caught.exception.detail)
            self.assertNotIn('private-key-sentinel', str(caught.exception.detail))

    def test_partial_update_checks_the_merged_certificate_pair(self):
        instance = SimpleNamespace(use_ssl=True, pg_ssl_mode='verify-full', client_cert=self.cert, client_key=self.key)
        self.assertEqual(self.validate({'client_key': self.key}, instance=instance)['client_key'], self.key)
        with self.assertRaises(ValidationError):
            self.validate({'client_key': ''}, instance=instance)

    def test_verification_mode_cannot_ignore_certificates_but_legacy_plaintext_is_unchanged(self):
        with self.assertRaises(ValidationError):
            self.validate({'use_ssl': True, 'pg_ssl_mode': 'verify-full', 'allow_invalid_cert': True})
        attrs = {'use_ssl': False, 'pg_ssl_mode': 'prefer'}
        self.assertEqual(self.validate(attrs.copy()), attrs)
