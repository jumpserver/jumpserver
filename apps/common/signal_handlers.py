# -*- coding: utf-8 -*-
#
import logging
import re
from collections import defaultdict

from django.conf import settings
from django.core.signals import request_finished
from django.db import connection
from django.db.models.signals import pre_save
from django.dispatch import receiver

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

    logger.debug(">>> [{}] {}".format(method, path))
    for name, counter in counters:
        logger.debug("Query {:3} times using {:.2f}s {}".format(
            counter.counter, counter.time, name)
        )

    on_request_finished_release_local(sender, **kwargs)


def on_request_finished_release_local(sender, **kwargs):
    thread_local.__release_local__()


def _get_request_user_name():
    user_name = 'System'
    current_request = get_current_request()
    if current_request and current_request.user.is_authenticated:
        user_name = current_request.user.name
        if isinstance(user_name, str):
            user_name = user_name[:30]
    return user_name


@receiver(pre_save)
def on_create_set_created_by(sender, instance=None, **kwargs):
    if getattr(instance, '_ignore_auto_created_by', False):
        return
    if not hasattr(instance, 'created_by') or instance.created_by:
        return
    user_name = _get_request_user_name()
    instance.created_by = user_name


@receiver(pre_save)
def on_update_set_updated_by(sender, instance=None, created=False, **kwargs):
    if getattr(instance, '_ignore_auto_updated_by', False):
        return
    if not hasattr(instance, 'updated_by'):
        return
    user_name = _get_request_user_name()
    instance.updated_by = user_name


if settings.DEBUG_DEV:
    request_finished.connect(on_request_finished_logging_db_query)
else:
    request_finished.connect(on_request_finished_release_local)
