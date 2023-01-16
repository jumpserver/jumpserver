# -*- coding: utf-8 -*-
#
import re
import os
import logging
from collections import defaultdict
from django.conf import settings
from django.core.signals import request_finished
from django.db import connection

from jumpserver.utils import get_current_request

from .local import thread_local

pattern = re.compile(r'FROM `(\w+)`')
logger = logging.getLogger("jumpserver.common")


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
    table_queries = defaultdict(list)

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
        table_queries[table_name].append(query)

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

    # print(">>> [{}] {}".format(method, path))
    # for table_name, queries in table_queries.items():
    #     if table_name.startswith('rbac_') or table_name.startswith('auth_permission'):
    #         continue
    #     print("- Table: {}".format(table_name))
    #     for i, query in enumerate(queries, 1):
    #         sql = query['sql']
    #         if not sql or not sql.startswith('SELECT'):
    #             continue
    #         print('\t{}. {}'.format(i, sql))

    on_request_finished_release_local(sender, **kwargs)


def on_request_finished_release_local(sender, **kwargs):
    thread_local.__release_local__()


if settings.DEBUG_DEV:
    request_finished.connect(on_request_finished_logging_db_query)
else:
    request_finished.connect(on_request_finished_release_local)
