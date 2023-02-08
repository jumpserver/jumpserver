# -*- coding: utf-8 -*-
#
import functools
import inspect
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from django.core.cache import cache
from django.db import transaction


def on_transaction_commit(func):
    """
    如果不调用on_commit, 对象创建时添加多对多字段值失败
    """

    def inner(*args, **kwargs):
        transaction.on_commit(lambda: func(*args, **kwargs))

    return inner


class Singleton(object):
    """ 单例类 """

    def __init__(self, cls):
        self._cls = cls
        self._instance = {}

    def __call__(self):
        if self._cls not in self._instance:
            self._instance[self._cls] = self._cls()
        return self._instance[self._cls]


def _run_func_if_is_last(ttl, func, *args, **kwargs):
    ix = uuid.uuid4().__str__()
    key = f'DELAY_RUN_{func.__name__}'
    cache.set(key, ix, ttl)
    st = (ttl - 2 > 1) and ttl - 2 or 2
    time.sleep(st)
    got = cache.get(key, None)

    if ix == got:
        func(*args, **kwargs)


executor = ThreadPoolExecutor(10)


def delay_run(ttl=5):
    def inner(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            executor.submit(_run_func_if_is_last, ttl, func, *args, **kwargs)

        return wrapper

    return inner


def _merge_run(ttl, func, *args, **kwargs):
    if not args or not isinstance(args[0], (list, tuple)):
        raise ValueError('args[0] must be list or tuple')

    key = f'DELAY_MERGE_RUN_{func.__name__}'
    ix = uuid.uuid4().__str__()
    value = cache.get(key, [])
    value.extend(args[0])

    st = (ttl - 2 > 1) and ttl - 2 or 2
    time.sleep(st)
    got = cache.get(key, None)

    if ix == got:
        func(*args, **kwargs)


def merge_delay_run(ttl):
    """
    合并 func 参数，延迟执行, 在 ttl 秒内, 只执行最后一次
    func 参数必须是 *args
    :param ttl:
    :return:
    """

    def inner(func):
        sigs = inspect.signature(func)
        if len(sigs.parameters) != 1:
            raise ValueError('func must have one arguments: %s' % func.__name__)
        param = list(sigs.parameters.values())[0]
        if not str(param).startswith('*'):
            raise ValueError('func args must be startswith *: %s' % func.__name__)

        @functools.wraps(func)
        def wrapper(*args):
            key = f'DELAY_MERGE_RUN_{func.__name__}'
            values = cache.get(key, [])
            new_arg = [*values, *args]
            cache.set(key, new_arg, ttl)
            return delay_run(ttl)(func)(*new_arg)

        return wrapper

    return inner


def delay_run(ttl=5):
    """
    延迟执行函数, 在 ttl 秒内, 只执行最后一次
    :param ttl:
    :return:
    """

    def inner(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            executor.submit(_run_func_if_is_last, ttl, func, *args, **kwargs)

        return wrapper

    return inner


@delay_run(ttl=10)
def test_delay_run(username, year=2000):
    print("Hello, %s, now is %s" % (username, year))


@merge_delay_run(ttl=10)
def test_merge_delay_run(*users):
    name = ','.join(users)
    print("Hello, %s, now is %s" % (name, time.time()))
