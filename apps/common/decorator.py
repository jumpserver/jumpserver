# -*- coding: utf-8 -*-
#
import functools
import threading
import time
import uuid

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
    st = (ttl - 2 > 1) and ttl - 2 or 1
    time.sleep(st)
    got = cache.get(key, None)

    if ix == got:
        func(*args, **kwargs)
        cache.delete(key)


def delay_run(ttl=5):
    def inner(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            t = threading.Thread(target=_run_func_if_is_last, args=(ttl, func, *args), kwargs=kwargs)
            t.start()

        return wrapper

    return inner


@delay_run(ttl=10)
def run_it_many(username, year=2000):
    print("Hello, %s, now is %s" % (username, year))


if __name__ == '__main__':
    for i in range(20):
        run_it_many('test', 2000)
