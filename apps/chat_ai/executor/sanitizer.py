import json
import re


SENSITIVE_KEYS = {
    'password', 'secret', 'token', 'access_token', 'refresh_token', 'access_key',
    'private_key', 'ssh_key', 'passphrase', 'cookie', 'authorization', 'api_key',
    'credential', 'secret_key',
}
SAFE_MARKER_KEYS = {'secret_provided', 'password_provided', 'credential_provided'}
REDACTED = '[REDACTED]'


def normalize_key(key):
    return re.sub(r'[^a-z0-9]+', '_', str(key).lower()).strip('_')


def is_sensitive_key(key):
    normalized = normalize_key(key)
    if normalized in SAFE_MARKER_KEYS:
        return False
    return normalized in SENSITIVE_KEYS or any(
        normalized.endswith(f'_{item}') or normalized.startswith(f'{item}_')
        for item in SENSITIVE_KEYS
    )


def contains_sensitive(value):
    if isinstance(value, dict):
        return any(is_sensitive_key(key) or contains_sensitive(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(contains_sensitive(item) for item in value)
    return False


def sanitize_text(value):
    text = str(value)
    text = re.sub(r'-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----', REDACTED, text, flags=re.S)
    text = re.sub(r'(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+', f'Bearer {REDACTED}', text)
    text = re.sub(r'\bsk-[A-Za-z0-9_-]{16,}\b', REDACTED, text)
    text = re.sub(r'\bAKIA[A-Z0-9]{16}\b', REDACTED, text)
    text = re.sub(
        r'(?i)\b(password|passphrase|secret|token|api[ _-]?key|authorization|cookie)\b\s*(?:is|[:=])\s*[^\s,;]+',
        lambda match: f'{match.group(1)}={REDACTED}', text,
    )
    text = re.sub(
        r'(密码|口令|密钥|令牌|私钥)\s*(?:是|为|[:：=])\s*[^\s,，；;]+',
        lambda match: f'{match.group(1)}={REDACTED}', text,
    )
    return text


def build_public_web_search_query(value, max_length=512):
    """Build a web query from user-authored text only."""
    text = re.sub(r'\s+', ' ', sanitize_text(value)).strip()
    return text[:max_length]


def sanitize(value, max_string=4096):
    if isinstance(value, dict):
        return {
            str(key): REDACTED if is_sensitive_key(key) else sanitize(item, max_string)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize(item, max_string) for item in value]
    if isinstance(value, str):
        return sanitize_text(value)[:max_string]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return sanitize_text(value)[:max_string]


def summarize(value, max_chars=8192):
    clean = sanitize(value)
    encoded = json.dumps(clean, ensure_ascii=False, default=str)
    if len(encoded) <= max_chars:
        return clean
    return {'truncated': True, 'preview': encoded[:max_chars]}
