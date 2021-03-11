import redis
from django.conf import settings


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

    def subscribe(self):
        ps = self.redis.pubsub()
        ps.subscribe(self.ch)
        return ps

    def publish(self, data):
        self.redis.publish(self.ch, data)
        return True
