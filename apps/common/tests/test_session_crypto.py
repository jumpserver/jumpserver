from types import SimpleNamespace
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase
from rest_framework import serializers

from common.serializers.fields import EncryptedField
from common.utils.crypto.rsa_aes import AESCrypto, RsaAesCryptoSuite, gen_key_pair
from common.utils.crypto.session import (
    ENCRYPTED_SEPARATOR, SessionDecryptError, decrypt_session_password,
)

LEGACY_SEPARATOR = ':'


class SessionPasswordEnvelopeTests(SimpleTestCase):
    password = 'P@ss:w0rd-with#colon'
    aes_key = 'k3yk3yk3y01'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.private_key, cls.public_key = gen_key_pair()
        _, cls.other_public_key = gen_key_pair()

    def setUp(self):
        self.session = {settings.SESSION_RSA_PRIVATE_KEY_NAME: self.private_key}
        request = SimpleNamespace(session=self.session, COOKIES={})
        patcher = patch('jumpserver.utils.current_request', request)
        patcher.start()
        self.addCleanup(patcher.stop)

    def envelope(self, separator=ENCRYPTED_SEPARATOR, public_key=None):
        suite = RsaAesCryptoSuite(None)
        key_cipher = suite.encrypt_with_key_pair(self.aes_key, public_key or self.public_key)
        password_cipher = AESCrypto(self.aes_key).encrypt(self.password)
        return f'{key_cipher}{separator}{password_cipher}'

    def test_current_envelope_is_decrypted(self):
        self.assertEqual(decrypt_session_password(self.envelope(), strict=True), self.password)

    def test_legacy_envelope_from_a_page_loaded_before_upgrade_is_decrypted(self):
        value = self.envelope(separator=LEGACY_SEPARATOR)
        self.assertEqual(decrypt_session_password(value, strict=True), self.password)
        self.assertEqual(decrypt_session_password(value), self.password)

    def test_plain_text_is_returned_unchanged(self):
        for value in ('', 'plain', 'ab:cd', 'CN=svc,DC=example,DC=com:secret', 'A' * 400):
            with self.subTest(value=value):
                self.assertEqual(decrypt_session_password(value, strict=True), value)
                self.assertEqual(decrypt_session_password(value), value)

    def test_strict_rejects_an_envelope_that_cannot_be_decrypted(self):
        for separator in (ENCRYPTED_SEPARATOR, LEGACY_SEPARATOR):
            value = self.envelope(separator=separator, public_key=self.other_public_key)
            with self.subTest(separator=separator), self.assertRaises(SessionDecryptError):
                decrypt_session_password(value, strict=True)

    def test_wrong_key_pair_raises_instead_of_returning_a_placeholder_key(self):
        suite = RsaAesCryptoSuite(None)
        key_cipher = suite.encrypt_with_key_pair(self.aes_key, self.other_public_key)
        with self.assertRaises(ValueError):
            suite.decrypt_with_key_pair(key_cipher, self.private_key)

    def test_strict_rejects_an_envelope_when_the_session_has_no_key(self):
        self.session.clear()
        with self.assertRaises(SessionDecryptError):
            decrypt_session_password(self.envelope(), strict=True)

    def test_non_strict_keeps_returning_an_undecryptable_envelope_unchanged(self):
        value = self.envelope(public_key=self.other_public_key)
        self.assertEqual(decrypt_session_password(value), value)

    def test_field_decrypts_current_and_legacy_envelopes(self):
        field = EncryptedField(max_length=1024)
        for separator in (ENCRYPTED_SEPARATOR, LEGACY_SEPARATOR):
            with self.subTest(separator=separator):
                value = self.envelope(separator=separator)
                self.assertEqual(field.run_validation(value), self.password)

    def test_field_keeps_plain_text(self):
        self.assertEqual(EncryptedField(max_length=1024).run_validation('ab:cd'), 'ab:cd')

    def test_field_rejects_an_envelope_instead_of_saving_the_ciphertext(self):
        field = EncryptedField(max_length=1024)
        for separator in (ENCRYPTED_SEPARATOR, LEGACY_SEPARATOR):
            value = self.envelope(separator=separator, public_key=self.other_public_key)
            with self.subTest(separator=separator):
                with self.assertRaises(serializers.ValidationError) as ctx:
                    field.run_validation(value)
                self.assertEqual(ctx.exception.detail[0].code, 'decrypt_failed')
