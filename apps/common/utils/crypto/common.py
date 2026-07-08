import re


secret_pattern = re.compile(r'password|secret|key|token', re.IGNORECASE)


def padding_key(key, max_length=32):
    """
    返回32 bytes 的key
    """
    if not isinstance(key, bytes):
        key = bytes(key, encoding='utf-8')

    if len(key) >= max_length:
        return key[:max_length]

    while len(key) % 16 != 0:
        key += b'\0'
    return key
