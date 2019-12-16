# -*- coding: utf-8 -*-
#
import re
import os
import logging
from collections import defaultdict
from django.conf import settings
from django.dispatch import receiver
from django.core.signals import request_finished
from django.db import connection
from django.conf import LazySettings
from django.db.utils import ProgrammingError, OperationalError

from jumpserver.utils import get_current_request

from .local import thread_local
from .signals import django_ready

pattern = re.compile(r'FROM `(\w+)`')
logger = logging.getLogger("jumpserver.common")
DEBUG_DB = os.environ.get('DEBUG_DB', '0') == '1'


class Counter:
    def __init__(self):
        self.counter = 0
        self.time = 0

    def __gt__(self, other):
        return self.counter > other.counter

    def __lt__(self, other):
        return self.counter < other.counter

    def __eq__(self, other):
        return self.counter == other.counter


def on_request_finished_logging_db_query(sender, **kwargs):
    queries = connection.queries
    counters = defaultdict(Counter)
    for query in queries:
        if not query['sql'] or not query['sql'].startswith('SELECT'):
            continue
        tables = pattern.findall(query['sql'])
        table_name = ''.join(tables)
        time = query['time']
        counters[table_name].counter += 1
        counters[table_name].time += float(time)
        counters['total'].counter += 1
        counters['total'].time += float(time)

    counters = sorted(counters.items(), key=lambda x: x[1])
    if not counters:
        return
    method = 'GET'
    path = '/Unknown'
    current_request = get_current_request()
    if current_request:
        method = current_request.method
        path = current_request.get_full_path()
    logger.debug(">>> [{}] {}".format(method, path))
    for name, counter in counters:
        logger.debug("Query {:3} times using {:.2f}s {}".format(
            counter.counter, counter.time, name)
        )


def on_request_finished_release_local(sender, **kwargs):
    thread_local.__release_local__()


if settings.DEBUG and DEBUG_DB:
    request_finished.connect(on_request_finished_logging_db_query)
else:
    request_finished.connect(on_request_finished_release_local)


@receiver(django_ready)
def monkey_patch_settings(sender, **kwargs):
    def monkey_patch_getattr(self, name):
        val = getattr(self._wrapped, name)
        if callable(val):
            val = val()
        return val

    try:
        LazySettings.__getattr__ = monkey_patch_getattr
    except (ProgrammingError, OperationalError):
        pass
