import re
from importlib import import_module

from django.conf import settings
from django.core.cache import caches
from django.utils import timezone

from jumpserver.utils import get_current_request


class SessionSaveMixin:
    ignore_pattern = re.compile(
        r'^/api/v1/(?:users/profile/|authentication/user-session/|authentication/session-lock/status/)'
    )

    def save(self, *args, **kwargs):
        request = get_current_request()
        # Read-only bootstrap/status polling must not renew a Web login.
        if request is not None and request.method in ('GET', 'HEAD') and self.ignore_pattern.match(request.path):
            return
        return super().save(*args, **kwargs)


def session_expiry(session_key):
    """Read the actual stored deadline for either supported Session backend."""
    store_class = import_module(settings.SESSION_ENGINE).SessionStore
    if hasattr(store_class, 'get_model_class'):
        return store_class.get_model_class().objects.filter(session_key=session_key).values_list('expire_date', flat=True).first()
    from datetime import timedelta
    store = store_class(session_key=session_key)
    ttl = caches[settings.SESSION_CACHE_ALIAS].pttl(store.cache_key)
    return timezone.now() + timedelta(milliseconds=ttl) if ttl is not None and ttl >= 0 else None
