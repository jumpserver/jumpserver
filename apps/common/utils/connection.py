import json
import threading
import time

import redis
from django.core.cache import cache
from redis.client import PubSub

from common.db.utils import safe_db_connection
from common.utils import get_logger

logger = get_logger(__name__)


def get_redis_client(db=0):
    client = cache.client.get_client()
    assert isinstance(client, redis.Redis)
    return client


class RedisPubSub:
    def __init__(self, ch, db=10):
        self.ch = ch
        self.db = db
        self.redis = get_redis_client(db)

    def subscribe(self, _next, error=None, complete=None):
        ps = self.redis.pubsub()
        ps.subscribe(self.ch)
        sub = Subscription(self, ps)
        sub.keep_handle_msg(_next, error, complete)
        return sub

    def resubscribe(self, _next, error=None, complete=None):
        self.redis = get_redis_client(self.db)
        self.subscribe(_next, error, complete)

    def publish(self, data):
        data_json = json.dumps(data)
        self.redis.publish(self.ch, data_json)
        return True


class Subscription:
    def __init__(self, pb: RedisPubSub, sub: PubSub):
        self.pb = pb
        self.ch = pb.ch
        self.sub = sub
        self.unsubscribed = False

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
            if self.unsubscribed:
                logger.debug('Subscription unsubscribed')
            else:
                logger.error('Consume msg error: {}'.format(e))
                self.retry(_next, error, complete)
                return

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
        self.unsubscribed = True
        try:
            self.sub.close()
        except Exception as e:
            logger.debug('Unsubscribe msg error: {}'.format(e))

    def retry(self, _next, error, complete):
        logger.info('Retry subscribe channel: {}'.format(self.ch))
        times = 0

        while True:
            try:
                self.unsubscribe()
                self.pb.resubscribe(_next, error, complete)
                break
            except Exception as e:
                logger.error('Retry #{} {} subscribe channel error: {}'.format(times, self.ch, e))
                times += 1
                time.sleep(times * 2)
