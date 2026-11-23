import base64
import binascii
import logging

from django.conf import settings

from .rsa_aes import  RsaAesCryptoSuite
from .gm import  GmCryptoSuite


ENCRYPTED_SEPARATOR = '::encrypted::'

# The browser wraps its one-time symmetric key with the session public key:
# 256 bytes for the RSA-2048 pair, about 113 bytes for SM2 (C1 + C3 + a 16 byte
# SM4 key). Anything shorter cannot be a key the browser wrapped.
MIN_KEY_CIPHER_BYTES = 96


class SessionDecryptError(ValueError):
    """The browser encrypted the value, but it could not be decrypted."""


def _b64_length(text):
    try:
        return len(base64.b64decode(text, altchars=b'-_', validate=True))
    except (binascii.Error, ValueError):
        return 0


# The web UI (lina, luna, static/js/session-encrypt.js) sends
#   base64(wrapped key) + ENCRYPTED_SEPARATOR + base64(cipher text)
# Any other value, including plain text that happens to contain the
# separator, is not an envelope.
def split_browser_envelope(value):
    """Return [key_cipher, password_cipher], or None when value is not an envelope."""
    if not isinstance(value, str):
        return None
    cipher = value.split(ENCRYPTED_SEPARATOR)
    if len(cipher) != 2:
        return None
    key_cipher, password_cipher = cipher
    if _b64_length(key_cipher) < MIN_KEY_CIPHER_BYTES:
        return None
    if not password_cipher or _b64_length(password_cipher) == 0:
        return None
    return cipher


# A value is only treated as encrypted when the session holds the private key
# the server issued to that browser (SessionCookieMiddleware) and the value is a
# well-formed browser envelope. Everything else, in particular API clients that
# send plain text and have no session key, is returned unchanged.
#
# strict=True raises SessionDecryptError when such an envelope cannot be
# decrypted (a tab still holding an older session key), instead of handing the
# ciphertext back to be saved as the secret.
def decrypt_session_password(value, strict=False):
    """Decrypt a value the browser encrypted with the session key pair."""
    from jumpserver.utils import current_request
    if not current_request or not value:
        return value

    private_key_name = settings.SESSION_RSA_PRIVATE_KEY_NAME
    private_key = current_request.session.get(private_key_name)
    if not private_key:
        return value

    cipher = split_browser_envelope(value)
    if cipher is None:
        return value
    key_cipher, password_cipher = cipher

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
