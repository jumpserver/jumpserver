"""Keep receipt tests (including AppConfig.ready hooks) off the dev database."""
import os
from copy import deepcopy

from jumpserver.settings import *  # noqa

DEBUG = False
DEBUG_DEV = False
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
redis_port = os.environ['MAGNUS_RECEIPT_TEST_REDIS_PORT']
CACHES = {
    name: {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://127.0.0.1:{redis_port}/0',
        'KEY_PREFIX': 'receipt-tests',
        'OPTIONS': {'CLIENT_CLASS': 'django_redis.client.DefaultClient', 'SOCKET_CONNECT_TIMEOUT': 1},
    } for name in CACHES
}
PASSWORD_HASHERS = ['django.contrib.auth.hashers.MD5PasswordHasher']
LOGGING = deepcopy(LOGGING)
for config in LOGGING.get('loggers', {}).values():
    config['level'] = 'ERROR'
