from redis_sessions.session import force_unicode, SessionStore as RedisSessionStore
from redis import exceptions


class SessionStore(RedisSessionStore):

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
