import json

import redis
from django.conf import settings

from common.db.utils import safe_db_connection
from common.utils import get_logger

logger = get_logger(__name__)


def get_redis_client(db):
    rc = redis.StrictRedis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
        db=db
    )
    return rc


class RedisPubSub:
    def __init__(self, ch, db=10):
        self.ch = ch
        self.redis = get_redis_client(db)
        self.subscriber = None

    def subscribe(self):
        ps = self.redis.pubsub()
        ps.subscribe(self.ch)
        return ps

    def publish(self, data):
        data_json = json.dumps(data)
        self.redis.publish(self.ch, data_json)
        return True

    def keep_handle_msg(self, handle):
        """
        handle arg is the pub published

        :param handle: lambda item: do_something
        :return:
        """
        self.close_handle_msg()
        sub = self.subscribe()
        self.subscriber = sub
        msgs = sub.listen()

        try:
            for msg in msgs:
                if msg["type"] != "message":
                    continue
                try:
                    item_json = msg['data'].decode()
                    item = json.loads(item_json)

                    with safe_db_connection():
                        handle(item)
                except Exception as e:
                    logger.error('Subscribe handler handle msg error: ', e)

        except Exception as e:
            logger.error('Consume msg error: ', e)

        try:
            sub.close()
        except Exception as e:
            logger.error("Redis observer close error: ", e)

    def close_handle_msg(self):
        if self.subscriber:
            self.subscriber.close()
            self.subscriber = None
