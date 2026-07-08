import logging
from django.conf import settings

from .rsa_aes import  RsaAesCryptoSuite
from .gm import  GmCryptoSuite


def decrypt_session_password(value):
    from jumpserver.utils import current_request
    if not current_request:
        return value

    cipher = value.split(':')
    if len(cipher) != 2:
        return value

    key_cipher, password_cipher = cipher
    if not all([key_cipher, password_cipher]):
        return value

    private_key_name = settings.SESSION_RSA_PRIVATE_KEY_NAME
    private_key = current_request.session.get(private_key_name)
    if not private_key or not value:
        return value

    cookie_gm_enabled = current_request.COOKIES.get('jms_gm_ssl', '0')
    gm_enabled = cookie_gm_enabled == '1'
    if gm_enabled:
        crypto_suite = GmCryptoSuite(None)
    else:
        crypto_suite = RsaAesCryptoSuite(None)

    key = crypto_suite.decrypt_with_key_pair(key_cipher, private_key)
    crypto_suite.key = key

    try:
        password = crypto_suite.decrypt(password_cipher)
    except Exception as e:
        logging.error("Decrypt password error: {}, {}".format(password_cipher, e))
        return value
    return password
