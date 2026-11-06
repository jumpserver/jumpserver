from django.core.cache import cache
from django.utils.crypto import salted_hmac
from rest_framework.exceptions import PermissionDenied

from audits.models import UserSession
from common.sessions import policy_locked


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
    if policy and 'locked' in policy:
        return policy_locked(policy)
    # Existing logins are adopted into their Session policy on the first status/save.
    legacy_locked = UserSession.objects.filter(key=session_key, user_id=user_id, is_locked=True).exists()
    return policy_locked(policy, legacy_locked=legacy_locked)


class WebSessionLocked(PermissionDenied):
    status_code = 423

    def __init__(self):
        super().__init__()
        self.detail = {'code': 'web_session_locked', 'locked': True}
