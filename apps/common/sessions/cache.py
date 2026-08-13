import re
import time
from importlib import import_module

from django.conf import settings
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
        if request is None or not self.ignore_pattern.match(request.path):
            try:
                super().save(*args, **kwargs)
            except Exception as e:
                logger.info(f'SessionStore save error: {e}')


class RedisUserSessionManager:
    PRESENCE_DEADLINES_KEY = 'jms_session_presence_deadlines'
    SESSION_CLEANUP_DEADLINES_KEY = 'jms_session_cleanup_deadlines'
    PRESENCE_LEASE_KEY_PREFIX = 'jms_session_presence_lease:'
    PRESENCE_RELEASE_KEY_PREFIX = 'jms_session_presence_release:'
    PRESENCE_LOCK_KEY_PREFIX = 'jms_session_presence_lock:'

    HEARTBEAT_INTERVAL = 30
    LEASE_TTL = 120
    SESSION_CLEANUP_TTL = 300
    RELEASE_GRACE_PERIOD = 10
    EXPIRED_BATCH_SIZE = 1000

    RENEW_SCRIPT = """
        redis.call('ZREMRANGEBYSCORE', KEYS[3], '-inf', ARGV[1])
        if redis.call('ZSCORE', KEYS[3], ARGV[3]) then
            return 0
        end

        redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])
        redis.call('ZADD', KEYS[1], ARGV[2], ARGV[3])
        redis.call('EXPIRE', KEYS[1], ARGV[4])
        redis.call('ZADD', KEYS[2], ARGV[2], ARGV[5])
        redis.call('ZADD', KEYS[4], ARGV[6], ARGV[5])
        return 1
    """

    RELEASE_SCRIPT = """
        redis.call('ZADD', KEYS[3], ARGV[6], ARGV[2])
        redis.call('EXPIRE', KEYS[3], ARGV[7])
        redis.call('ZREM', KEYS[1], ARGV[2])
        redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', ARGV[1])

        local lease = redis.call('ZREVRANGE', KEYS[1], 0, 0, 'WITHSCORES')
        if #lease > 0 then
            local deadline = tonumber(lease[2])
            local ttl = math.max(
                1, deadline - tonumber(ARGV[1]) + tonumber(ARGV[5])
            )
            redis.call('ZADD', KEYS[2], deadline, ARGV[3])
            redis.call('EXPIRE', KEYS[1], ttl)
            return 1
        end

        redis.call('DEL', KEYS[1])
        redis.call('ZADD', KEYS[2], ARGV[4], ARGV[3])
        redis.call('ZADD', KEYS[4], ARGV[4], ARGV[3])
        return 0
    """

    POP_EXPIRED_SCRIPT = """
        local sessions = redis.call(
            'ZRANGEBYSCORE', KEYS[1], '-inf', ARGV[1],
            'LIMIT', 0, ARGV[2]
        )
        if #sessions > 0 then
            redis.call('ZREM', KEYS[1], unpack(sessions))
        end
        return sessions
    """

    def __init__(self):
        self.client = cache.client.get_client()

    @staticmethod
    def _decode(value):
        return value.decode('utf-8') if isinstance(value, bytes) else value

    def _lease_key(self, session_key):
        return f'{self.PRESENCE_LEASE_KEY_PREFIX}{session_key}'

    def _release_key(self, session_key):
        return f'{self.PRESENCE_RELEASE_KEY_PREFIX}{session_key}'

    def _lock(self, session_key):
        key = f'{self.PRESENCE_LOCK_KEY_PREFIX}{session_key}'
        return self.client.lock(key, timeout=10, blocking_timeout=5)

    @staticmethod
    def _session_exists(session_key):
        session_store_cls = import_module(settings.SESSION_ENGINE).SessionStore
        return session_store_cls().exists(session_key)

    @staticmethod
    def _session_expires_at_browser_close(session_key):
        session_store_cls = import_module(settings.SESSION_ENGINE).SessionStore
        session_store = session_store_cls(session_key=session_key)
        if not session_store.exists(session_key):
            return None
        return session_store.get_expire_at_browser_close()

    def renew(self, session_key, client_id):
        if not session_key:
            return None

        with self._lock(session_key):
            if not self._session_exists(session_key):
                return None

            now = int(time.time())
            deadline = now + self.LEASE_TTL
            cleanup_deadline = now + self.SESSION_CLEANUP_TTL
            lease_expiration = self.LEASE_TTL + self.HEARTBEAT_INTERVAL
            renewed = self.client.eval(
                self.RENEW_SCRIPT,
                4,
                self._lease_key(session_key),
                self.PRESENCE_DEADLINES_KEY,
                self._release_key(session_key),
                self.SESSION_CLEANUP_DEADLINES_KEY,
                now,
                deadline,
                client_id,
                lease_expiration,
                session_key,
                cleanup_deadline,
            )
        return bool(renewed)

    def release(self, session_key, client_id):
        if not session_key:
            return False

        with self._lock(session_key):
            now = int(time.time())
            deadline = now + self.RELEASE_GRACE_PERIOD
            release_deadline = now + self.LEASE_TTL
            release_expiration = self.LEASE_TTL + self.HEARTBEAT_INTERVAL
            return bool(self.client.eval(
                self.RELEASE_SCRIPT,
                4,
                self._lease_key(session_key),
                self.PRESENCE_DEADLINES_KEY,
                self._release_key(session_key),
                self.SESSION_CLEANUP_DEADLINES_KEY,
                now,
                client_id,
                session_key,
                deadline,
                self.HEARTBEAT_INTERVAL,
                release_deadline,
                release_expiration,
            ))

    def remove(self, session_key):
        if not session_key:
            return

        try:
            with self._lock(session_key):
                self._remove(session_key)
        except Exception:
            pass

    def _remove(self, session_key):
        try:
            self.client.zrem(self.PRESENCE_DEADLINES_KEY, session_key)
            self.client.zrem(self.SESSION_CLEANUP_DEADLINES_KEY, session_key)
            self.client.delete(self._lease_key(session_key))
            self.client.delete(self._release_key(session_key))
            session_store = import_module(settings.SESSION_ENGINE).SessionStore(session_key)
            session_store.delete()
            return True
        except Exception:
            return False

    def remove_if_inactive(self, session_key, browser_close_only=False):
        with self._lock(session_key):
            if self._check_presence_active(session_key):
                return False
            if browser_close_only:
                expires_at_browser_close = self._session_expires_at_browser_close(
                    session_key
                )
                if expires_at_browser_close is False:
                    return False
            return self._remove(session_key)

    def _check_presence_active(self, session_key, now=None):
        deadline = self.client.zscore(self.PRESENCE_DEADLINES_KEY, session_key)
        return deadline is not None and deadline > (now or time.time())

    def check_active(self, session_key):
        return self._check_presence_active(session_key)

    def get_active_keys(self):
        now = time.time()
        stored_session_keys = set(self.get_keys())
        session_keys = {
            self._decode(key) for key in self.client.zrangebyscore(
                self.PRESENCE_DEADLINES_KEY, f'({now}', '+inf'
            )
        }
        session_keys.intersection_update(stored_session_keys)
        return list(session_keys)

    def pop_expired_keys(self):
        keys = self.client.eval(
            self.POP_EXPIRED_SCRIPT,
            1,
            self.SESSION_CLEANUP_DEADLINES_KEY,
            time.time(),
            self.EXPIRED_BATCH_SIZE,
        )
        return [self._decode(key) for key in keys]

    @staticmethod
    def get_keys():
        session_store_cls = import_module(settings.SESSION_ENGINE).SessionStore
        cache_key_prefix = session_store_cls.cache_key_prefix
        keys = caches[settings.SESSION_CACHE_ALIAS].iter_keys('*')
        return [k.replace(cache_key_prefix, '') for k in keys]


user_session_manager = RedisUserSessionManager()
