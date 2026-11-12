from django_redis.pool import ConnectionFactory, SentinelConnectionFactory


# django-redis caches pools by URL. Separate registries isolate long-lived
# subscriptions and blocking locks even when they share the cache database.
class BlockingConnectionFactory(ConnectionFactory):
    _pools = {}


class BlockingSentinelConnectionFactory(SentinelConnectionFactory):
    _pools = {}


class PubSubConnectionFactory(ConnectionFactory):
    _pools = {}


class PubSubSentinelConnectionFactory(SentinelConnectionFactory):
    _pools = {}
