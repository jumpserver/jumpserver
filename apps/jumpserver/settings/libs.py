# -*- coding: utf-8 -*-
#
import os

from .base import (
    REDIS_SSL_CA, REDIS_SSL_CERT, REDIS_SSL_KEY, REDIS_SSL_REQUIRED, REDIS_USE_SSL,
    REDIS_PROTOCOL, REDIS_SENTINEL_SERVICE_NAME, REDIS_SENTINELS, REDIS_SENTINEL_PASSWORD,
    REDIS_SENTINEL_SOCKET_TIMEOUT
)
from ..const import CONFIG, PROJECT_DIR

REST_FRAMEWORK = {
    # Use Django's standard `django.contrib.auth` permissions,
    # or allow read-only access for unauthenticated users.
    'DEFAULT_PERMISSION_CLASSES': (
        'rbac.permissions.RBACPermission',
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'common.drf.renders.CSVFileRenderer',
        'common.drf.renders.ExcelFileRenderer',
    ),
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.FormParser',
        'rest_framework.parsers.MultiPartParser',
        'common.drf.parsers.CSVFileParser',
        'common.drf.parsers.ExcelFileParser',
        'rest_framework.parsers.FileUploadParser',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        # 'rest_framework.authentication.BasicAuthentication',
        'authentication.backends.drf.AccessTokenAuthentication',
        'authentication.backends.drf.PrivateTokenAuthentication',
        'authentication.backends.drf.SignatureAuthentication',
        'authentication.backends.drf.SessionAuthentication',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_METADATA_CLASS': 'common.drf.metadata.SimpleMetadataWithFilters',
    'ORDERING_PARAM': "order",
    'SEARCH_PARAM': "search",
    'DATETIME_FORMAT': '%Y/%m/%d %H:%M:%S %z',
    'DATETIME_INPUT_FORMATS': ['%Y/%m/%d %H:%M:%S %z', 'iso-8601', '%Y-%m-%d %H:%M:%S %z'],
    'DEFAULT_PAGINATION_CLASS': 'jumpserver.rewriting.pagination.MaxLimitOffsetPagination',
    'PAGE_SIZE': CONFIG.DEFAULT_PAGE_SIZE,
    'EXCEPTION_HANDLER': 'common.drf.exc_handlers.common_exception_handler',
}

SWAGGER_SETTINGS = {
    'DEFAULT_AUTO_SCHEMA_CLASS': 'jumpserver.views.swagger.CustomSwaggerAutoSchema',
    'USE_SESSION_AUTH': True,
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'DEFAULT_INFO': 'jumpserver.views.swagger.api_info',
}

# Captcha settings, more see https://django-simple-captcha.readthedocs.io/en/latest/advanced.html
CAPTCHA_IMAGE_SIZE = (180, 38)
CAPTCHA_FOREGROUND_COLOR = '#001100'
CAPTCHA_NOISE_FUNCTIONS = ('captcha.helpers.noise_dots',)
CAPTCHA_CHALLENGE_FUNCT = 'captcha.helpers.math_challenge'

# Django bootstrap3 setting, more see http://django-bootstrap3.readthedocs.io/en/latest/settings.html
BOOTSTRAP3 = {
    'horizontal_label_class': 'col-md-2',
    'horizontal_field_class': 'col-md-9',
    # Set placeholder attributes to label if no placeholder is provided
    'set_placeholder': False,
    'success_css_class': '',
    'required_css_class': 'required',
}

# Django channels support websocket
REDIS_LAYERS_HOST = {
    'db': CONFIG.REDIS_DB_WS,
}

REDIS_LAYERS_SSL_PARAMS = {}
if REDIS_USE_SSL:
    REDIS_LAYERS_SSL_PARAMS.update({
        'ssl_cert_reqs': REDIS_SSL_REQUIRED,
        "ssl_keyfile": REDIS_SSL_KEY,
        "ssl_certfile": REDIS_SSL_CERT,
        "ssl_ca_certs": REDIS_SSL_CA
    })
    REDIS_LAYERS_HOST.update(REDIS_LAYERS_SSL_PARAMS)

if REDIS_SENTINEL_SERVICE_NAME and REDIS_SENTINELS:
    REDIS_LAYERS_HOST['sentinels'] = REDIS_SENTINELS
    REDIS_LAYERS_HOST['password'] = CONFIG.REDIS_PASSWORD or None
    REDIS_LAYERS_HOST['master_name'] = REDIS_SENTINEL_SERVICE_NAME
    REDIS_LAYERS_HOST['sentinel_kwargs'] = {
        'password': REDIS_SENTINEL_PASSWORD,
        'socket_timeout': REDIS_SENTINEL_SOCKET_TIMEOUT,
        'ssl': REDIS_USE_SSL,
        'ssl_cert_reqs': REDIS_SSL_REQUIRED,
        "ssl_keyfile": REDIS_SSL_KEY,
        "ssl_certfile": REDIS_SSL_CERT,
        "ssl_ca_certs": REDIS_SSL_CA
    }
else:
    # More info see: https://github.com/django/channels_redis/issues/334
    # REDIS_LAYERS_HOST['address'] = (CONFIG.REDIS_HOST, CONFIG.REDIS_PORT)
    REDIS_LAYERS_ADDRESS = '{protocol}://:{password}@{host}:{port}/{db}'.format(
        protocol=REDIS_PROTOCOL, password=CONFIG.REDIS_PASSWORD_QUOTE,
        host=CONFIG.REDIS_HOST, port=CONFIG.REDIS_PORT, db=CONFIG.REDIS_DB_WS
    )
    REDIS_LAYERS_HOST['address'] = REDIS_LAYERS_ADDRESS

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'common.cache.RedisChannelLayer',
        'CONFIG': {
            "hosts": [REDIS_LAYERS_HOST],
        },
    },
}

ASGI_APPLICATION = 'jumpserver.routing.application'

# Dump all celery log to here
CELERY_LOG_DIR = os.path.join(PROJECT_DIR, 'data', 'celery')

# Celery using redis as broker
CELERY_BROKER_URL_FORMAT = '%(protocol)s://:%(password)s@%(host)s:%(port)s/%(db)s'
if REDIS_SENTINEL_SERVICE_NAME and REDIS_SENTINELS:
    CELERY_BROKER_URL = ';'.join([CELERY_BROKER_URL_FORMAT % {
        'protocol': 'sentinel', 'password': CONFIG.REDIS_PASSWORD,
        'host': item[0], 'port': item[1], 'db': CONFIG.REDIS_DB_CELERY
    } for item in REDIS_SENTINELS])
    SENTINEL_OPTIONS = {
        'master_name': REDIS_SENTINEL_SERVICE_NAME,
        'sentinel_kwargs': {
            'password': REDIS_SENTINEL_PASSWORD,
            'socket_timeout': REDIS_SENTINEL_SOCKET_TIMEOUT,
            'ssl': REDIS_USE_SSL,
            'ssl_cert_reqs': REDIS_SSL_REQUIRED,
            "ssl_keyfile": REDIS_SSL_KEY,
            "ssl_certfile": REDIS_SSL_CERT,
            "ssl_ca_certs": REDIS_SSL_CA
        }
    }
    CELERY_BROKER_TRANSPORT_OPTIONS = CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = SENTINEL_OPTIONS
else:
    CELERY_BROKER_URL = CELERY_BROKER_URL_FORMAT % {
        'protocol': REDIS_PROTOCOL,
        'password': CONFIG.REDIS_PASSWORD_QUOTE,
        'host': CONFIG.REDIS_HOST,
        'port': CONFIG.REDIS_PORT,
        'db': CONFIG.REDIS_DB_CELERY,
    }
CELERY_TIMEZONE = CONFIG.TIME_ZONE
CELERY_ENABLE_UTC = False
CELERY_TASK_SERIALIZER = 'pickle'
CELERY_RESULT_SERIALIZER = 'pickle'
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ['json', 'pickle']
CELERY_RESULT_EXPIRES = 600
CELERY_WORKER_TASK_LOG_FORMAT = '%(message)s'
CELERY_WORKER_LOG_FORMAT = '%(message)s'
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_WORKER_REDIRECT_STDOUTS = True
CELERY_WORKER_REDIRECT_STDOUTS_LEVEL = "INFO"
CELERY_TASK_SOFT_TIME_LIMIT = 3600
CELERY_WORKER_CANCEL_LONG_RUNNING_TASKS_ON_CONNECTION_LOSS = True

if REDIS_USE_SSL:
    CELERY_BROKER_USE_SSL = CELERY_REDIS_BACKEND_USE_SSL = {
        'ssl_cert_reqs': REDIS_SSL_REQUIRED,
        'ssl_ca_certs': REDIS_SSL_CA,
        'ssl_certfile': REDIS_SSL_CERT,
        'ssl_keyfile': REDIS_SSL_KEY
    }

ANSIBLE_LOG_DIR = os.path.join(PROJECT_DIR, 'data', 'ansible')

#
REDIS_HOST = CONFIG.REDIS_HOST
REDIS_PORT = CONFIG.REDIS_PORT
REDIS_PASSWORD = CONFIG.REDIS_PASSWORD
REDIS_PASSWORD_QUOTE = CONFIG.REDIS_PASSWORD_QUOTE

DJANGO_REDIS_SCAN_ITERSIZE = 1000

# GM DEVICE
PIICO_DEVICE_ENABLE = CONFIG.PIICO_DEVICE_ENABLE
PIICO_DRIVER_PATH = CONFIG.PIICO_DRIVER_PATH
