import json
import threading
import redis

from django.core.cache import cache

from common.db.utils import safe_db_connection
from common.utils import get_logger

logger = get_logger(__name__)


def get_redis_client(db=0):
    client = cache.client.get_client()
    assert isinstance(client, redis.Redis)
    return client


class Subscription:
    def __init__(self, ch, sub, ):
        self.ch = ch
        self.sub = sub

    def _handle_msg(self, _next, error, complete):
        """
        handle arg is the pub published

        :param _next: next msg handler
        :param error: error msg handler
        :param complete: complete msg handler
        :return:
        """
        msgs = self.sub.listen()

        if error is None:
            error = lambda m, i: None

        if complete is None:
            complete = lambda: None

        try:
            for msg in msgs:
                if msg["type"] != "message":
                    continue
                item = None
                try:
                    item_json = msg['data'].decode()
                    item = json.loads(item_json)

                    with safe_db_connection():
                        _next(item)
                except Exception as e:
                    error(msg, item)
                    logger.error('Subscribe handler handle msg error: {}'.format(e))
        except Exception as e:
            # 正常的 websocket 断开时, redis 会断开连接，避免日志太多
            # logger.error('Consume msg error: {}'.format(e))
            pass

        try:
            complete()
        except Exception as e:
            logger.error('Complete subscribe error: {}'.format(e))
            pass

        try:
            self.unsubscribe()
        except Exception as e:
            logger.error("Redis observer close error: {}".format(e))

    def keep_handle_msg(self, _next, error, complete):
        t = threading.Thread(target=self._handle_msg, args=(_next, error, complete))
        t.daemon = True
        t.start()
        return t

    def unsubscribe(self):
        try:
            self.sub.close()
        except Exception as e:
            logger.error('Unsubscribe msg error: {}'.format(e))


class RedisPubSub:
    def __init__(self, ch, db=10):
        self.ch = ch
        self.redis = get_redis_client(db)

    def subscribe(self, _next, error=None, complete=None):
        ps = self.redis.pubsub()
        ps.subscribe(self.ch)
        sub = Subscription(self.ch, ps)
        sub.keep_handle_msg(_next, error, complete)
        return sub

    def publish(self, data):
        data_json = json.dumps(data)
        self.redis.publish(self.ch, data_json)
        return True
