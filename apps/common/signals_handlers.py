# -*- coding: utf-8 -*-
#
import re
from collections import defaultdict
from django.conf import settings
from django.dispatch import receiver
from django.core.signals import request_finished
from django.db import connection


from common.utils import get_logger
from .local import thread_local

pattern = re.compile(r'FROM `(\w+)`')
# logger = logging.getLogger('jmsdb')
logger = get_logger(__name__)


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
        if not query['sql'].startswith('SELECT'):
            continue
        tables = pattern.findall(query['sql'])
        table_name = ''.join(tables)
        time = query['time']
        counters[table_name].counter += 1
        counters[table_name].time += float(time)
        counters['total'].counter += 1
        counters['total'].time += float(time)

    counters = sorted(counters.items(), key=lambda x: x[1])
    for name, counter in counters:
        logger.debug("Query {:3} times using {:.2f}s {}".format(
            counter.counter, counter.time, name)
        )


@receiver(request_finished)
def on_request_finished_release_local(sender, **kwargs):
    thread_local.__release_local__()


if settings.DEBUG:
    request_finished.connect(on_request_finished_logging_db_query)






