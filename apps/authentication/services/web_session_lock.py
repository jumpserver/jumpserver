from django.core.cache import cache
from django.utils.crypto import salted_hmac
from rest_framework.exceptions import PermissionDenied

from audits.models import UserSession
from common.sessions import closed_pages_locked


def session_scope(session_key):
    # Public correlation ID for tabs; never expose the Session cookie itself.
    return salted_hmac('web-screen-lock-scope', session_key).hexdigest()


def lock_cache_key(session_key):
    return 'web-session-lock:' + session_scope(session_key)


def clear_web_session_cache(session_key):
    if not session_key:
        return
    cache.delete_many([
        lock_cache_key(session_key),
        'web-session-renewal:' + salted_hmac('session-renewal', session_key).hexdigest(),
    ])


def session_locked(session_key, user_id, policy):
    # The stored deadline also applies with no page open; no timer or cache write is needed.
    if closed_pages_locked(policy):
        return True
    key = lock_cache_key(session_key)
    locked = cache.get(key)
    if locked is None:
        locked = UserSession.objects.filter(key=session_key, user_id=user_id, is_locked=True).exists()
        # A concurrent lock/unlock must win over an older cache-miss reader.
        cache.add(key, locked, timeout=60)
        locked = cache.get(key, locked)
    return locked


class WebSessionLocked(PermissionDenied):
    status_code = 423

    def __init__(self):
        super().__init__()
        self.detail = {'code': 'web_session_locked', 'locked': True}
