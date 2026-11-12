import json
import threading

import redis
from django.core.cache import caches
from redis.client import PubSub

from common.db.utils import safe_db_connection
from common.utils import get_logger

logger = get_logger(__name__)


def get_redis_client(db=0, *, cache_alias='default'):
    client = caches[cache_alias].client.get_client()
    assert isinstance(client, redis.Redis)
    return client


class RedisPubSub:
    def __init__(self, ch, db=10):
        self.ch = ch
        self.db = db
        self.redis = get_redis_client(db)

    def _new_pubsub(self):
        ps = get_redis_client(self.db, cache_alias='pubsub').pubsub()
        try:
            ps.subscribe(self.ch)
        except BaseException:
            ps.close()
            raise
        return ps

    def subscribe(self, _next, error=None, complete=None):
        sub = Subscription(self, self._new_pubsub())
        try:
            sub.keep_handle_msg(_next, error, complete)
        except BaseException:
            sub.unsubscribe()
            raise
        return sub

    def resubscribe(self, _next, error=None, complete=None):
        self.redis = get_redis_client(self.db)
        return self.subscribe(_next, error, complete)

    def publish(self, data):
        data_json = json.dumps(data)
        self.redis.publish(self.ch, data_json)
        return True


class Subscription:
    def __init__(self, pb: RedisPubSub, sub: PubSub):
        self.pb = pb
        self.ch = pb.ch
        self.sub = sub
        self._stopped = threading.Event()
        self._pubsub_lock = threading.Lock()

    @property
    def unsubscribed(self):
        return self._stopped.is_set()

    def _handle_msg(self, _next, error, complete):
        """
        handle arg is the pub published
        :param _next: next msg handler
        :param error: error msg handler
        :param complete: complete msg handler
        :return:
        """
        if error is None:
            error = lambda m, i: None

        if complete is None:
            complete = lambda: None

        try:
            while not self.unsubscribed:
                try:
                    while not self.unsubscribed and self.sub.subscribed:
                        # Serialize PubSub I/O and cleanup; user callbacks do not
                        # hold this lock, so cancelling a slow callback releases Redis.
                        with self._pubsub_lock:
                            if self.unsubscribed:
                                break
                            msg = self.sub.get_message(timeout=1)
                        if self.unsubscribed:
                            break
                        if not msg or msg['type'] != 'message':
                            continue
                        item = None
                        try:
                            item = json.loads(msg['data'].decode())
                            with safe_db_connection():
                                _next(item)
                        except Exception as e:
                            error(msg, item)
                            logger.error('Subscribe handler handle msg error: {}'.format(e))
                    break
                except Exception as e:
                    if self.unsubscribed:
                        break
                    logger.error('Consume msg error: {}'.format(e))
                    if not self.retry():
                        break
        finally:
            self.unsubscribe()
            with self._pubsub_lock:
                self._close_pubsub()
            try:
                complete()
            except Exception as e:
                logger.error('Complete subscribe error: {}'.format(e))

    def keep_handle_msg(self, _next, error, complete):
        t = threading.Thread(target=self._handle_msg, args=(_next, error, complete))
        t.daemon = True
        t.start()
        return t

    def unsubscribe(self):
        self._stopped.set()
        # Do not block the ASGI event loop waiting for an in-flight Redis read.
        # The listener's finally handles that case once its bounded read finishes.
        if self._pubsub_lock.acquire(blocking=False):
            try:
                self._close_pubsub()
            finally:
                self._pubsub_lock.release()

    def _close_pubsub(self):
        # Called with _pubsub_lock held; Redis PubSub.reset is not thread-safe.
        if self.sub.connection is None:
            return
        try:
            self.sub.close()
        except Exception as e:
            logger.warning(f'Unsubscribe msg error: {e}')

    def retry(self):
        logger.info('Retry subscribe channel: {}'.format(self.ch))
        with self._pubsub_lock:
            self._close_pubsub()
        times = 0
        while not self.unsubscribed:
            try:
                with self._pubsub_lock:
                    if self.unsubscribed:
                        break
                    # Keep the original Subscription handle and its stop signal.
                    self.sub = self.pb._new_pubsub()
                return not self.unsubscribed
            except Exception as e:
                logger.error('Retry #{} {} subscribe channel error: {}'.format(times, self.ch, e))
                times += 1
                if self._stopped.wait(min(times * 2, 30)):
                    break
        return False
