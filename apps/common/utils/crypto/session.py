import logging
import re

from django.conf import settings

from .rsa_aes import  RsaAesCryptoSuite
from .gm import  GmCryptoSuite


ENCRYPTED_SEPARATOR = '::encrypted::'

# Envelope sent by UI builds that predate ENCRYPTED_SEPARATOR:
#   base64(asymmetric(aes_key)) + ':' + base64(symmetric(password))
# A page that was loaded before an upgrade keeps sending this format until it
# is reloaded, so it has to be recognised instead of being taken for plain text.
LEGACY_ENVELOPE_PATTERN = re.compile(r'^[A-Za-z0-9+/=]{100,}:[A-Za-z0-9+/=]{16,}$')


class SessionDecryptError(ValueError):
    """The value is an encrypted envelope, but it could not be decrypted."""


def split_envelope(value):
    """Return [key_cipher, password_cipher], or None when value is plain text."""
    if ENCRYPTED_SEPARATOR in value:
        cipher = value.split(ENCRYPTED_SEPARATOR)
    elif LEGACY_ENVELOPE_PATTERN.match(value):
        cipher = value.split(':')
    else:
        return None

    if len(cipher) != 2 or not all(cipher):
        return None
    return cipher


def decrypt_session_password(value, strict=False):
    """Decrypt a value the browser encrypted with the session key pair.

    strict=False keeps the historical behaviour: a value that cannot be
    decrypted is returned unchanged (API clients send plain text).

    strict=True raises SessionDecryptError when the value is an encrypted
    envelope that cannot be decrypted, so that the ciphertext is never saved
    as if it were the secret itself.
    """
    from jumpserver.utils import current_request
    if not current_request or not value:
        return value

    cipher = split_envelope(value)
    if cipher is None:
        return value
    key_cipher, password_cipher = cipher

    private_key_name = settings.SESSION_RSA_PRIVATE_KEY_NAME
    private_key = current_request.session.get(private_key_name)
    if not private_key:
        if strict:
            raise SessionDecryptError('No session key to decrypt the field')
        return value

    cookie_gm_enabled = current_request.COOKIES.get('jms_gm_ssl', '0')
    gm_enabled = cookie_gm_enabled == '1'
    if gm_enabled:
        crypto_suite = GmCryptoSuite(None)
    else:
        crypto_suite = RsaAesCryptoSuite(None)

    try:
        key = crypto_suite.decrypt_with_key_pair(key_cipher, private_key)
        crypto_suite.key = key
        password = crypto_suite.decrypt(password_cipher)
    except Exception as e:
        logging.error("Decrypt password error: {}".format(e))
        if strict:
            raise SessionDecryptError(str(e)) from e
        return value
    return password
