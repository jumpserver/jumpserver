from django.core.cache import cache
from django.utils.crypto import salted_hmac
from rest_framework.exceptions import PermissionDenied


def session_scope(session_key):
    # Public correlation ID for tabs; never expose the Session cookie itself.
    return salted_hmac('web-screen-lock-scope', session_key).hexdigest()


def clear_web_session_cache(session_key):
    if not session_key:
        return
    cache.delete('web-session-renewal:' + salted_hmac('session-renewal', session_key).hexdigest())


class WebSessionLocked(PermissionDenied):
    status_code = 423

    def __init__(self):
        super().__init__()
        self.detail = {'code': 'web_session_locked', 'locked': True}
