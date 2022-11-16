# -*- coding: utf-8 -*-
#
import re
import logging
import time
import threading

from collections import defaultdict

from common.signals import django_ready
from redis.sentinel import SentinelConnectionPool
from django.core.cache import cache
from django.dispatch import receiver
from django.conf import settings
from django.core.signals import request_finished
from django.db import connection

from settings.signal_handlers import subscribe_settings_change
from orgs.signal_handlers.common import subscribe_orgs_mapping_expire
from assets.signal_handlers.node_assets_mapping import subscribe_node_assets_mapping_expire
from jumpserver.utils import get_current_request

from .local import thread_local

pattern = re.compile(r'FROM `(\w+)`')
logger = logging.getLogger("jumpserver.common")


global_subscribe_threading_list = []


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


if settings.DEBUG_DEV:
    request_finished.connect(on_request_finished_logging_db_query)
else:
    request_finished.connect(on_request_finished_release_local)


@receiver(django_ready)
def start_subscribe_tasks(**kwargs):
    tasks = (
        subscribe_settings_change,
        subscribe_node_assets_mapping_expire,
        subscribe_orgs_mapping_expire
    )

    for t_func in tasks:
        global_subscribe_threading_list.append(t_func())


def stop_subscribe_tasks():
    global global_subscribe_threading_list

    for t in global_subscribe_threading_list:
        try:
            t.stop()
        except:
            pass

    global_subscribe_threading_list = []


def check_sentinel_is_switch(client):
    service_name = settings.REDIS_SENTINEL_SERVICE_NAME
    sentinel_manager = client.connection_pool.sentinel_manager
    ready_redis = sentinel_manager.discover_master(service_name)
    while True:
        try:
            current_redis = sentinel_manager.discover_master(service_name)
            if ready_redis != current_redis:
                logger.info('Redis switch from %s to %s' % (
                    ready_redis, current_redis
                ))
                stop_subscribe_tasks()
                start_subscribe_tasks()
                ready_redis = current_redis
        except:
            pass
        time.sleep(2)


@receiver(django_ready)
def start_sentinel_check(sender, **kwargs):
    client = cache.client.get_client()
    if isinstance(client.connection_pool, SentinelConnectionPool):
        t = threading.Thread(target=check_sentinel_is_switch, args=(client,))
        t.daemon = True
        t.start()
