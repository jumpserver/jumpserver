import base64
import binascii
from typing import Union

from Cryptodome.Util.asn1 import DerSequence
from gmssl import sm2


BytesOrStr = Union[bytes, str]


def _decode_text(value):
    text = value.strip()
    if not text:
        return None

    try:
        return bytes.fromhex(text)
    except ValueError:
        pass

    padding = '=' * (-len(text) % 4)
    try:
        return base64.b64decode((text + padding).encode(), altchars=b'-_', validate=True)
    except (binascii.Error, ValueError):
        return None


def _to_bytes(value):
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return _decode_text(value)
    return None


def _normalize_public_key(public_key):
    key = _to_bytes(public_key)
    if key is None:
        return None
    if len(key) == 65 and key[0] == 4:
        key = key[1:]
    if len(key) != 64:
        return None
    return key.hex()


def _decode_der_signature(signature):
    try:
        decoded = DerSequence().decode(signature)
        if len(decoded) != 2:
            return None
        r, s = int(decoded[0]), int(decoded[1])
        if not (0 <= r < 1 << 256 and 0 <= s < 1 << 256):
            return None
        return f'{r:064x}{s:064x}'
    except (ValueError, IndexError, TypeError):
        return None


def _normalize_signature(signature):
    sign = _to_bytes(signature)
    if sign is None:
        return None
    der_signature = _decode_der_signature(sign) if sign.startswith(b'0') else None
    if der_signature:
        return der_signature
    if len(sign) == 64:
        return sign.hex()
    return _decode_der_signature(sign)


def _normalize_digest(digest):
    data = _to_bytes(digest)
    if data is None:
        return None
    return data


def _new_verifier(public_key):
    normalized_public_key = _normalize_public_key(public_key)
    if not normalized_public_key:
        return None
    return sm2.CryptSM2(private_key='', public_key=normalized_public_key)


def verify_usbkey_signature(public_key: BytesOrStr, digest: BytesOrStr, signature: BytesOrStr) -> bool:
    try:
        verifier = _new_verifier(public_key)
        normalized_digest = _normalize_digest(digest)
        normalized_signature = _normalize_signature(signature)
        if not verifier or normalized_digest is None or not normalized_signature:
            return False
        return bool(verifier.verify(normalized_signature, normalized_digest))
    except Exception:
        return False


def verify_usbkey_sm2_data(public_key: BytesOrStr, data: bytes, signature: BytesOrStr) -> bool:
    try:
        verifier = _new_verifier(public_key)
        normalized_signature = _normalize_signature(signature)
        if not verifier or not isinstance(data, bytes) or not normalized_signature:
            return False
        return bool(verifier.verify_with_sm3(normalized_signature, data))
    except Exception:
        return False
