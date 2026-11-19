"""Server-owned credential namespaces. Never fall back to raw cache keys."""

import re
from uuid import UUID

from django.core.cache import cache


BEARER_TOKEN_KEY = 'auth:bearer-token:{token}'
BEARER_INDEX_KEY = 'auth:bearer-index:{user_id}:{remote_addr}'
TICKET_DIRECT_APPROVE_KEY = 'ticket:direct-approve:{token}'
PASSWORD_PREVIEW_KEY = 'auth:password-preview:{token}'
PASSWORD_PREVIEW_VERIFIED_KEY = 'auth:password-preview-verified:{token}'
PASSWORD_PREVIEW_SEND_AT_KEY = 'auth:password-preview-send-at:{token}'
PASSWORD_PREVIEW_USER_SEND_AT_KEY = 'auth:password-preview-user-send-at:{username}'


def valid_token_format(token, length):
    return (
        isinstance(token, str) and len(token) == length
        and re.fullmatch(r'[a-zA-Z0-9]+', token) is not None
    )


def valid_uuid(value):
    if isinstance(value, UUID):
        return True
    if not isinstance(value, str):
        return False
    try:
        UUID(value)
    except ValueError:
        return False
    return True


def get_password_preview(token):
    if not valid_token_format(token, 36):
        return None
    data = cache.get(PASSWORD_PREVIEW_KEY.format(token=token))
    # Only validate fields consumed by the preview page and verification flow.
    if not isinstance(data, dict) or not isinstance(data.get('username'), str):
        return None
    if not data['username']:
        return None
    if 'phone' not in data or not isinstance(data['phone'], (str, type(None))):
        return None
    return data
