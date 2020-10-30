from __future__ import unicode_literals

import sys
import logging
from logging.handlers import SysLogHandler
from django.apps import AppConfig
from django.conf import settings


def set_rsyslog():
    logger = logging.getLogger('syslog')
    host, port = settings.SYSLOG_ADDR.split(':')
    address = (host, int(port))
    handler = SysLogHandler(
        address=address,
        facility=settings.SYSLOG_FACILITY,
        socktype=settings.SYSLOG_SOCKTYPE
    )
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)


class CommonConfig(AppConfig):
    name = 'common'

    def ready(self):
        from . import signals_handlers
        from .signals import django_ready
        if 'migrate' not in sys.argv:
            django_ready.send(CommonConfig)
        if settings.SYSLOG_ENABLE:
            set_rsyslog()

