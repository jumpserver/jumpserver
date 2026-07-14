import base64
import binascii
import hashlib
import hmac
import json
import time
import uuid

from django.conf import settings

from .signing import SigningKeyUnavailable, get_signing_key


HEADER_NAME = 'X-JMS-AI-Delegation'
OPERATION_HEADER_NAME = 'X-JMS-AI-Operation'
MAX_TTL = 60


def _encode(value):
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode()


def _decode(value):
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))


def _signing_key(key_id):
    return get_signing_key(
        key_id=key_id,
        key_id_setting='CHAT_AI_DELEGATION_KEY_ID',
        secret_setting='CHAT_AI_DELEGATION_SECRET',
        verify_keys_setting='CHAT_AI_DELEGATION_VERIFY_KEYS',
        purpose='jumpserver-chat-ai-delegation-v1',
    )


def _signature(encoded_payload, key_id):
    return hmac.new(_signing_key(key_id), encoded_payload.encode(), hashlib.sha256).hexdigest()


def request_binding_hash(method, path, query_string=b'', body=b''):
    if isinstance(query_string, str):
        query_string = query_string.encode()
    if isinstance(body, str):
        body = body.encode()
    value = b'\0'.join((method.upper().encode(), path.encode(), query_string, body))
    return hashlib.sha256(value).hexdigest()


def issue_delegation(
    *, user_id, org_id, conversation_id, approval_id, operation_id, method,
    path, request_hash, ttl=30,
):
    now = int(time.time())
    key_id = str(getattr(settings, 'CHAT_AI_DELEGATION_KEY_ID', 'v1') or 'v1')
    payload = {
        'issuer': getattr(settings, 'CHAT_AI_DELEGATION_ISSUER', 'jumpserver-ai'),
        'audience': getattr(settings, 'CHAT_AI_DELEGATION_AUDIENCE', 'jumpserver-core'),
        'key_id': key_id,
        'user_id': str(user_id),
        'org_id': str(org_id),
        'conversation_id': str(conversation_id or ''),
        'approval_id': str(approval_id or ''),
        'allowed_operation_id': operation_id,
        'method': method.upper(),
        'path': path,
        'request_hash': request_hash,
        'issued_at': now,
        'expires_at': now + min(max(1, ttl), MAX_TTL),
        'nonce': uuid.uuid4().hex,
    }
    encoded = _encode(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode())
    return f'{encoded}.{_signature(encoded, key_id)}'


def verify_delegation(token):
    try:
        if not isinstance(token, str) or len(token) > 4096:
            return None
        encoded, supplied_signature = token.split('.', 1)
        payload = json.loads(_decode(encoded))
        key_id = str(payload.get('key_id') or '')
        if not hmac.compare_digest(supplied_signature, _signature(encoded, key_id)):
            return None
    except (
        ValueError, TypeError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError,
        SigningKeyUnavailable,
    ):
        return None
    now = int(time.time())
    try:
        issued_at = int(payload.get('issued_at') or 0)
        expires_at = int(payload.get('expires_at') or 0)
    except (TypeError, ValueError):
        return None
    if issued_at > now + 5 or expires_at < now or expires_at - issued_at > MAX_TTL:
        return None
    required = {
        'issuer', 'audience', 'key_id', 'user_id', 'org_id',
        'allowed_operation_id', 'method', 'path', 'request_hash', 'nonce',
    }
    if not all(payload.get(key) for key in required):
        return None
    if payload['issuer'] != getattr(settings, 'CHAT_AI_DELEGATION_ISSUER', 'jumpserver-ai'):
        return None
    if payload['audience'] != getattr(settings, 'CHAT_AI_DELEGATION_AUDIENCE', 'jumpserver-core'):
        return None
    return payload
