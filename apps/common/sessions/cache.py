from importlib import import_module

from django.conf import settings
from django.contrib.sessions.backends.cache import (
    SessionStore as DjangoSessionStore
)
from django.core.cache import caches

from . import SessionSaveMixin


class SessionStore(SessionSaveMixin, DjangoSessionStore):
    pass


class RedisUserSessionManager:
    def remove(self, session_key):
        try:
            session_store = import_module(settings.SESSION_ENGINE).SessionStore(session_key)
            session_store.delete()
        except Exception:
            pass

    @staticmethod
    def check_active(session_key):
        from . import session_login_policies
        return bool(session_login_policies([session_key]).get(session_key))

    def get_active_keys(self):
        from . import session_login_policies
        return [key for key, policy in session_login_policies(self.get_keys()).items() if policy]

    @staticmethod
    def get_keys():
        session_store_cls = import_module(settings.SESSION_ENGINE).SessionStore
        if hasattr(session_store_cls, 'get_model_class'):
            from django.utils import timezone
            return list(session_store_cls.get_model_class().objects.filter(
                expire_date__gt=timezone.now(),
            ).values_list('session_key', flat=True))
        cache_key_prefix = session_store_cls.cache_key_prefix
        keys = caches[settings.SESSION_CACHE_ALIAS].iter_keys('*')
        return [k.replace(cache_key_prefix, '') for k in keys]


user_session_manager = RedisUserSessionManager()
