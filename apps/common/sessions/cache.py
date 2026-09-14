import re
from importlib import import_module

from django.conf import settings
from django.contrib.auth import SESSION_KEY
from django.contrib.sessions.backends.cache import (
    SessionStore as DjangoSessionStore
)
from django.core.cache import cache, caches

from common.utils import get_logger
from jumpserver.utils import get_current_request

logger = get_logger(__file__)


class SessionStore(DjangoSessionStore):
    ignore_urls = [
        r'^/api/v1/users/profile/',
        r'^/api/v1/authentication/user-session/'
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ignore_pattern = re.compile('|'.join(self.ignore_urls))

    def save(self, *args, **kwargs):
        request = get_current_request()
        if (
            request is not None and self.ignore_pattern.match(request.path)
            and not self._should_renew_for_asset_session(request)
        ):
            return
        try:
            super().save(*args, **kwargs)
        except Exception as e:
            logger.info(f'SessionStore save error: {e}')

    def _should_renew_for_asset_session(self, request):
        if request.method != 'GET' or request.path != '/api/v1/users/profile/':
            return False

        try:
            user = getattr(request, 'user', None)
            if (
                not self.session_key or user is None or not user.is_authenticated
                or not user.is_valid
            ):
                return False
            user_id = str(user.pk)
            if self.get(SESSION_KEY) != user_id:
                return False

            from orgs.utils import tmp_to_root_org
            from terminal.models import Session

            # Asset sessions in any organization can keep this user's login alive.
            with tmp_to_root_org():
                session_ids = Session.objects.filter(
                    user_id=user_id, is_finished=False
                ).values_list('id', flat=True)
                keys = [Session.ACTIVE_CACHE_KEY_PREFIX.format(i) for i in session_ids]
            return bool(keys) and any(cache.get_many(keys).values())
        except Exception as e:
            logger.warning('Failed to check asset sessions for login renewal: %s', type(e).__name__)
            return False


class RedisUserSessionManager:
    JMS_SESSION_KEY = 'jms_session_key'

    def __init__(self):
        self.client = cache.client.get_client()

    def add_or_increment(self, session_key):
        self.client.hincrby(self.JMS_SESSION_KEY, session_key, 1)

    def decrement(self, session_key):
        self.client.hincrby(self.JMS_SESSION_KEY, session_key, -1)

    def remove(self, session_key):
        try:
            self.client.hdel(self.JMS_SESSION_KEY, session_key)
            session_store = import_module(settings.SESSION_ENGINE).SessionStore(session_key)
            session_store.delete()
        except Exception:
            pass

    def check_active(self, session_key):
        count = self.client.hget(self.JMS_SESSION_KEY, session_key)
        count = 0 if count is None else int(count.decode('utf-8'))
        return count > 0

    def get_active_keys(self):
        session_keys = []
        for k, v in self.client.hgetall(self.JMS_SESSION_KEY).items():
            count = int(v.decode('utf-8'))
            if count <= 0:
                continue
            key = k.decode('utf-8')
            session_keys.append(key)
        return session_keys

    @staticmethod
    def get_keys():
        session_store_cls = import_module(settings.SESSION_ENGINE).SessionStore
        cache_key_prefix = session_store_cls.cache_key_prefix
        keys = caches[settings.SESSION_CACHE_ALIAS].iter_keys('*')
        return [k.replace(cache_key_prefix, '') for k in keys]


user_session_manager = RedisUserSessionManager()
