from django_redis.pool import ConnectionFactory, SentinelConnectionFactory


# django-redis caches pools by URL. A separate registry keeps the blocking
# alias isolated even though it uses the same URL/database as the default cache.
class BlockingConnectionFactory(ConnectionFactory):
    _pools = {}


class BlockingSentinelConnectionFactory(SentinelConnectionFactory):
    _pools = {}
