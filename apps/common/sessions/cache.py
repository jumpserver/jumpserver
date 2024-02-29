import re

from django.contrib.sessions.backends.cache import (
    SessionStore as DjangoSessionStore
)
from django.core.cache import cache

from jumpserver.utils import get_current_request


class SessionStore(DjangoSessionStore):
    ignore_urls = [
        r'^/api/v1/users/profile/'
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ignore_pattern = re.compile('|'.join(self.ignore_urls))

    def save(self, *args, **kwargs):
        request = get_current_request()
        if request is None or not self.ignore_pattern.match(request.path):
            super().save(*args, **kwargs)


class RedisUserSessionManager:
    JMS_SESSION_KEY = 'jms_session_key'

    def __init__(self):
        self.client = cache.client.get_client()

    def add_or_increment(self, session_key):
        self.client.hincrby(self.JMS_SESSION_KEY, session_key, 1)

    def decrement_or_remove(self, session_key):
        new_count = self.client.hincrby(self.JMS_SESSION_KEY, session_key, -1)
        if new_count <= 0:
            self.client.hdel(self.JMS_SESSION_KEY, session_key)

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


user_session_manager = RedisUserSessionManager()
