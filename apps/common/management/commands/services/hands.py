import logging
import os
import sys

from django.conf import settings

from apps.jumpserver.const import CONFIG

try:
    from apps.jumpserver import const

    __version__ = const.VERSION
except ImportError as e:
    print("Not found __version__: {}".format(e))
    print("Python is: ")
    logging.info(sys.executable)
    __version__ = 'Unknown'
    sys.exit(1)

HTTP_HOST = CONFIG.HTTP_BIND_HOST or '127.0.0.1'
HTTP_PORT = CONFIG.HTTP_LISTEN_PORT or 8080
WS_PORT = CONFIG.WS_LISTEN_PORT or 8082
DEBUG = CONFIG.DEBUG or False
BASE_DIR = os.path.dirname(settings.BASE_DIR)
LOG_DIR = os.path.join(BASE_DIR, 'data', 'logs')
APPS_DIR = os.path.join(BASE_DIR, 'apps')
TMP_DIR = os.path.join(BASE_DIR, 'tmp')
