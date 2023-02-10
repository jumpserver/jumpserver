# -*- coding: utf-8 -*-
#
import asyncio
import functools
import inspect
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

from django.core.cache import cache
from django.db import transaction

from .utils import logger


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


def default_suffix_key(*args, **kwargs):
    return 'default'


def key_by_org(*args, **kwargs):
    return args[0].org_id


def _run_func_if_is_last(ttl, suffix_key, org, func, *args, **kwargs):
    from orgs.utils import set_current_org

    try:
        set_current_org(org)
        uid = uuid.uuid4().__str__()
        suffix_key_func = suffix_key if suffix_key else default_suffix_key
        func_name = f'{func.__module__}_{func.__name__}'
        key_suffix = suffix_key_func(*args, **kwargs)
        key = f'DELAY_RUN_{func_name}_{key_suffix}'
        cache.set(key, uid, ttl)
        st = (ttl - 2 > 1) and ttl - 2 or 2
        time.sleep(st)
        ret = cache.get(key, None)

        if uid == ret:
            func(*args, **kwargs)
    except Exception as e:
        logger.error('delay run error: %s' % e)


class LoopThread(threading.Thread):
    def __init__(self, loop, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loop = loop

    def run(self) -> None:
        asyncio.set_event_loop(loop)
        self.loop.run_forever()
        print('loop stopped')


loop = asyncio.get_event_loop()
loop_thread = LoopThread(loop)
loop_thread.daemon = True
loop_thread.start()
executor = ThreadPoolExecutor(max_workers=5, thread_name_prefix='debouncer')


class Debouncer(object):
    def __init__(self, callback, check, delay, *args, **kwargs):
        self.callback = callback
        self.check = check
        self.delay = delay

    async def __call__(self, *args, **kwargs):
        await asyncio.sleep(self.delay)
        ok = await self._check(*args, **kwargs)
        if ok:
            await loop.run_in_executor(executor, self.callback, *args)

    async def _check(self, *args, **kwargs):
        if asyncio.iscoroutinefunction(self.check):
            return await self.check(*args, **kwargs)
        return await loop.run_in_executor(executor, self.check)


def _run_func_with_org(org, func, *args, **kwargs):
    from orgs.utils import set_current_org

    try:
        set_current_org(org)
        func(*args, **kwargs)
    except Exception as e:
        logger.error('delay run error: %s' % e)


def delay_run(ttl=5, key=None):
    """
    延迟执行函数, 在 ttl 秒内, 只执行最后一次
    :param ttl:
    :param key: 是否合并参数, 一个 callback
    :return:
    """

    def inner(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from orgs.utils import get_current_org
            org = get_current_org()
            suffix_key_func = key if key else default_suffix_key
            uid = uuid.uuid4().__str__()
            func_name = f'{func.__module__}_{func.__name__}'
            key_suffix = suffix_key_func(*args, **kwargs)
            cache_key = f'DELAY_RUN_{func_name}_{key_suffix}'
            # 延迟两倍时间，防止缓存过期，导致校验失败
            cache.set(cache_key, uid, ttl * 2)

            def _check_func(key_id, key_value):
                ret = cache.get(key_id, None)
                return key_value == ret

            check_func_partial = functools.partial(_check_func, cache_key, uid)
            run_func_partial = functools.partial(_run_func_with_org, org, func)
            asyncio.run_coroutine_threadsafe(
                Debouncer(run_func_partial, check_func_partial, ttl)(*args, **kwargs),
                loop=loop
            )

        return wrapper

    return inner


def merge_delay_run(ttl, key=None):
    """
    合并 func 参数，延迟执行, 在 ttl 秒内, 只执行最后一次
    func 参数必须是 *args
    :param ttl:
    :param key: 是否合并参数, 一个 callback
    :return:
    """

    def inner(func):
        sigs = inspect.signature(func)
        if len(sigs.parameters) != 1:
            raise ValueError('func must have one arguments: %s' % func.__name__)
        param = list(sigs.parameters.values())[0]
        if not str(param).startswith('*'):
            raise ValueError('func args must be startswith *: %s' % func.__name__)

        suffix_key_func = key if key else default_suffix_key

        @functools.wraps(func)
        def wrapper(*args):
            key_suffix = suffix_key_func(*args)
            func_name = f'{func.__module__}_{func.__name__}'
            cache_key = f'DELAY_MERGE_RUN_{func_name}_{key_suffix}'
            values = cache.get(cache_key, [])
            new_arg = [*values, *args]
            cache.set(cache_key, new_arg, ttl)
            return delay_run(ttl, suffix_key_func)(func)(*new_arg)

        return wrapper

    return inner


@delay_run(ttl=5)
def test_delay_run(username, year=2000):
    print("Hello, %s, now is %s" % (username, year))


@merge_delay_run(ttl=5, key=lambda *users: users[0][0])
def test_merge_delay_run(*users):
    name = ','.join(users)
    time.sleep(2)
    print("Hello, %s, now is %s" % (name, time.time()))


@merge_delay_run(ttl=5, key=lambda *users: users[0][0])
def test_merge_delay_run(*users):
    name = ','.join(users)
    time.sleep(2)
    print("Hello, %s, now is %s" % (name, time.time()))


def do_test():
    s = time.time()
    print("start : %s" % time.time())
    for i in range(100):
        # test_delay_run('test', year=i)
        test_merge_delay_run('test %s' % i)
        test_merge_delay_run('best %s' % i)

    end = time.time()
    using = end - s
    print("end : %s, using: %s" % (end, using))
