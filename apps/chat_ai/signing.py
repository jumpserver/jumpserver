import hashlib
import hmac

from django.conf import settings


class SigningKeyUnavailable(Exception):
    pass


def get_signing_key(*, key_id, key_id_setting, secret_setting, verify_keys_setting, purpose):
    active_key_id = str(getattr(settings, key_id_setting, 'v1') or 'v1')
    if key_id == active_key_id:
        configured = getattr(settings, secret_setting, '') or ''
        if configured:
            return str(configured).encode()
        return hmac.new(
            settings.SECRET_KEY.encode(),
            purpose.encode(),
            hashlib.sha256,
        ).digest()

    verify_keys = getattr(settings, verify_keys_setting, {}) or {}
    configured = verify_keys.get(key_id)
    if not configured:
        raise SigningKeyUnavailable(f'Unknown signing key: {key_id}')
    return str(configured).encode()
