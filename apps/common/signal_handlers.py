# -*- coding: utf-8 -*-
#
import os
import re
from collections import defaultdict

from django.conf import settings
from django.core.signals import request_finished
from django.db import connection
from django.db.models.signals import pre_save
from django.dispatch import receiver

from jumpserver.utils import get_current_request
from .local import thread_local
from .signals import django_ready
from .utils import get_logger

pattern = re.compile(r'FROM `(\w+)`')
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


def digest_sql_query():
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

    print(">>>. [{}] {}".format(method, path))
    for table_name, queries in table_queries.items():
        if table_name.startswith('rbac_') or table_name.startswith('auth_permission'):
            continue

        for query in queries:
            sql = query['sql']
            print(" # {}: {}".format(query['time'], sql[:1000]))
        if len(queries) < 3:
            continue
        print("- Table: {}".format(table_name))
        for i, query in enumerate(queries, 1):
            sql = query['sql']
            if not sql or not sql.startswith('SELECT'):
                continue
            print('\t{}.[{}s] {}'.format(i, round(float(query['time']), 2), sql[:1000]))

    # logger.debug(">>> [{}] {}".format(method, path))
    for name, counter in counters:
        logger.debug("Query {:3} times using {:.2f}s {}".format(
            counter.counter, counter.time, name)
        )


def on_request_finished_logging_db_query(sender, **kwargs):
    digest_sql_query()
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


@receiver(django_ready)
def check_migrations_file_prefix_conflict(*args, **kwargs):
    if not settings.DEBUG_DEV:
        return

    from jumpserver.const import BASE_DIR
    print('>>> Check migrations file prefix conflict.', end=' ')
    # 指定 app 目录
    _dir = BASE_DIR
    # 获取所有子目录
    sub_dirs = next(os.walk(_dir))[1]
    # 记录冲突的文件，元素为 (subdir, file1, file2)
    conflict_files = []

    # 遍历每个子目录
    for subdir in sub_dirs:
        # 拼接 migrations 目录路径
        migrations_dir = os.path.join(_dir, subdir, 'migrations')
        # 判断是否存在 migrations 目录
        if not os.path.exists(migrations_dir):
            continue
        # 获取所有文件名
        files = os.listdir(migrations_dir)
        # 遍历每个文件名
        prefix_file_map = dict()
        for file in files:
            file = str(file)
            # 判断是否为 Python 文件
            if not file.endswith('.py'):
                continue
            if 'squashed' in file:
                continue
            # file 为文件名
            file_prefix = file.split('_')[0]
            if file_prefix in prefix_file_map.keys():
                conflict_files.append((subdir, file, prefix_file_map.get(file_prefix)))
            else:
                prefix_file_map[file_prefix] = file

    conflict_count = len(conflict_files)
    print(f'Conflict count:({conflict_count})')
    if not conflict_count:
        return

    print('=' * 80)
    for conflict_file in conflict_files:
        msg_dir = '{:<15}'.format(conflict_file[0])
        msg_split = '=> '
        msg_left = msg_dir
        msg_right1 = msg_split + '{:<80}'.format(conflict_file[1])
        msg_right2 = ' ' * len(msg_left) + msg_split + conflict_file[2]
        print(f'{msg_left}{msg_right1}\n{msg_right2}\n')

    print('=' * 80)
