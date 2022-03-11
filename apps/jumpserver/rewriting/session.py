from redis_sessions.session import (
    force_unicode, SessionStore as RedisSessionStore,
    RedisServer as RedisRedisServer, settings as redis_setting
)
from redis import exceptions, Redis
from django.conf import settings

from jumpserver.const import CONFIG


class RedisServer(RedisRedisServer):
    __redis = {}

    def get(self):
        if self.connection_key in self.__redis:
            return self.__redis[self.connection_key]

        ssl_params = {}
        if CONFIG.REDIS_USE_SSL:
            ssl_params = {
                'ssl_keyfile': getattr(settings, 'REDIS_SSL_KEYFILE'),
                'ssl_certfile': getattr(settings, 'REDIS_SSL_CERTFILE'),
                'ssl_ca_certs': getattr(settings, 'REDIS_SSL_CA_CERTS'),
            }
        # 只根据 redis_url 方式连接
        self.__redis[self.connection_key] = Redis.from_url(
            redis_setting.SESSION_REDIS_URL, **ssl_params
        )

        return self.__redis[self.connection_key]


class SessionStore(RedisSessionStore):
    def __init__(self, session_key=None):
        super(SessionStore, self).__init__(session_key)
        self.server = RedisServer(session_key).get()

    def load(self):
        try:
            session_data = self.server.get(
                self.get_real_stored_key(self._get_or_create_session_key())
            )
            return self.decode(force_unicode(session_data))
        except exceptions.ConnectionError as e:
            # 解决redis服务异常(如: 主从切换时)，用户session立即过期的问题
            raise
        except:
            self._session_key = None
            return {}
