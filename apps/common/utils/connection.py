import json
import threading
import time

import redis
from django.core.cache import cache

from common.db.utils import safe_db_connection
from common.utils import get_logger

logger = get_logger(__name__)


def get_redis_client(db=0):
    client = cache.client.get_client()
    assert isinstance(client, redis.Redis)
    return client


class RedisPubSub:
    handlers = {}
    lock = threading.Lock()
    redis = get_redis_client()
    pubsub = redis.pubsub()

    def __init__(self, ch, db=10):
        self.ch = ch
        self.db = db

    def subscribe(self, _next, error=None, complete=None):
        with self.lock:
            if self.ch not in self.handlers:
                self.pubsub.subscribe(self.ch)
            self.handlers[self.ch] = _next

        sub = Subscription(self, self.handlers)
        sub.keep_handle_msg(self.handlers, error, complete)
        return sub

    @classmethod
    def resubscribe(cls, handles, error=None, complete=None):
        for ch, handler in handles.items():
            cls(ch).subscribe(handler, error, complete)

    def publish(self, data):
        data_json = json.dumps(data)
        self.redis.publish(self.ch, data_json)
        return True


class Subscription:
    running = False

    def __init__(self, pb: RedisPubSub, handlers: dict):
        self.pb = pb
        self.ch = pb.ch
        self.unsubscribed = False
        self.sub = self.pb.pubsub
        self.handlers = handlers

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
                channel = msg['channel'].decode()
                handler = self.handlers.get(channel)
                item = None
                try:
                    item_json = msg['data'].decode()
                    item = json.loads(item_json)

                    with safe_db_connection():
                        handler(item)
                except Exception as e:
                    error(msg, item)
                    logger.error('Subscribe handler handle msg error: {}'.format(e))
        except Exception as e:
            if self.unsubscribed:
                logger.debug('Subscription unsubscribed')
            else:
                logger.error('Consume msg error: {}'.format(e))
                self.retry(self.handlers, error, complete)
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

    def keep_handle_msg(self, handlers, error, complete):
        if not self.running:
            self.running = True
            t = threading.Thread(target=self._handle_msg, args=(handlers, error, complete))
            t.daemon = True
            t.start()

    def unsubscribe(self):
        self.unsubscribed = True
        logger.info(f"Unsubscribed from channel: {self.sub}")
        try:
            self.pb.pubsub.close()
        except Exception as e:
            logger.warning(f'Unsubscribe msg error: {e}')

    def retry(self, handlers, error, complete):
        logger.info('Retry subscribe channel: {}'.format(self.ch))
        times = 0

        while True:
            try:
                self.unsubscribe()
                self.pb.resubscribe(handlers, error, complete)
                break
            except Exception as e:
                logger.error('Retry #{} {} subscribe channel error: {}'.format(times, self.ch, e))
                times += 1
                time.sleep(times * 2)
