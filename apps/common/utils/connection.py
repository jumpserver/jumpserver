import json
import time

import redis
from django.core.cache import cache

from common.db.utils import safe_db_connection
from common.utils import get_logger

logger = get_logger(__name__)

import threading
from concurrent.futures import ThreadPoolExecutor

_PUBSUB_HUBS = {}


def _get_pubsub_hub(db=10):
    hub = _PUBSUB_HUBS.get(db)
    if not hub:
        hub = PubSubHub(db=db)
        _PUBSUB_HUBS[db] = hub
    return hub


class PubSubHub:

    def __init__(self, db=10):
        self.db = db
        self.redis = get_redis_client(db)
        self.pubsub = self.redis.pubsub()
        self.handlers = {}
        self.lock = threading.RLock()
        self.listener = None
        self.running = False
        self.executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix='pubsub_handler')

    def __del__(self):
        self.executor.shutdown(wait=True)

    def start(self):
        with self.lock:
            if self.listener and self.listener.is_alive():
                return
            self.running = True
            self.listener = threading.Thread(name='pubsub_listen', target=self._listen_loop, daemon=True)
            self.listener.start()

    def _listen_loop(self):
        backoff = 1
        while self.running:
            try:
                for msg in self.pubsub.listen():
                    if msg.get("type") != "message":
                        continue
                    ch = msg.get("channel")
                    if isinstance(ch, bytes):
                        ch = ch.decode()
                    data = msg.get("data")
                    try:
                        if isinstance(data, bytes):
                            item = json.loads(data.decode())
                        elif isinstance(data, str):
                            item = json.loads(data)
                        else:
                            item = data
                    except Exception:
                        item = data
                    # 使用线程池处理消息
                    future = self.executor.submit(self._dispatch, ch, msg, item)
                    future.add_done_callback(
                        lambda f: f.exception() and logger.error(f"handle pubsub msg {msg} failed: {f.exception()}"))
                backoff = 1
            except Exception as e:
                logger.error(f'PubSub listen error: {e}')
                time.sleep(backoff)
                backoff = min(backoff * 2, 30)
                try:
                    self._reconnect()
                except Exception as re:
                    logger.error(f'PubSub reconnect error: {re}')

    def _dispatch(self, ch, raw_msg, item):
        with self.lock:
            handler = self.handlers.get(ch)
        if not handler:
            return
        _next, error, _complete = handler
        try:
            with safe_db_connection():
                _next(item)
        except Exception as e:
            logger.error(f'Subscribe handler handle msg error: {e}')
            try:
                if error:
                    error(raw_msg, item)
            except Exception:
                pass

    def add_subscription(self, pb, _next, error, complete):
        ch = pb.ch
        with self.lock:
            existed = bool(self.handlers.get(ch))
            self.handlers[ch] = (_next, error, complete)
            try:
                if not existed:
                    self.pubsub.subscribe(ch)
            except Exception as e:
                logger.error(f'Subscribe channel {ch} error: {e}')
        self.start()
        return Subscription(pb=pb, hub=self, ch=ch, handler=(_next, error, complete))

    def remove_subscription(self, sub):
        ch = sub.ch
        with self.lock:
            existed = self.handlers.pop(ch, None)
            if existed:
                try:
                    self.pubsub.unsubscribe(ch)
                except Exception as e:
                    logger.warning(f'Unsubscribe {ch} error: {e}')

    def _reconnect(self):
        with self.lock:
            channels = [ch for ch, h in self.handlers.items() if h]
            try:
                self.pubsub.close()
            except Exception:
                pass
            self.redis = get_redis_client(self.db)
            self.pubsub = self.redis.pubsub()
            if channels:
                self.pubsub.subscribe(channels)


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
        hub = _get_pubsub_hub(self.db)
        return hub.add_subscription(self, _next, error, complete)

    def resubscribe(self, _next, error=None, complete=None):
        return self.subscribe(_next, error, complete)

    def publish(self, data):
        data_json = json.dumps(data)
        self.redis.publish(self.ch, data_json)
        return True


class Subscription:
    def __init__(self, pb: RedisPubSub, hub: PubSubHub, ch: str, handler):
        self.pb = pb
        self.ch = ch
        self.hub = hub
        self.handler = handler
        self.unsubscribed = False

    def unsubscribe(self):
        if self.unsubscribed:
            return
        self.unsubscribed = True
        logger.info(f"Unsubscribed from channel: {self.ch}")
        try:
            self.hub.remove_subscription(self)
        except Exception as e:
            logger.warning(f'Unsubscribe msg error: {e}')
