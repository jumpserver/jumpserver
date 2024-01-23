# -*- coding: utf-8 -*-
#
import asyncio
import functools
import inspect
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

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
    values = list(kwargs.values())
    if not values:
        return 'default'
    return values[0][0].org_id


class EventLoopThread(threading.Thread):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._loop = asyncio.new_event_loop()

    def run(self) -> None:
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_forever()
        except Exception as e:
            logger.error("Event loop stopped with err: {} ".format(e))

    def get_loop(self):
        return self._loop


_loop_thread = EventLoopThread()
_loop_thread.daemon = True
_loop_thread.start()
executor = ThreadPoolExecutor(
    max_workers=10,
    thread_name_prefix='debouncer'
)
_loop_debouncer_func_task_cache = {}
_loop_debouncer_func_args_cache = {}
_loop_debouncer_func_task_time_cache = {}


def get_loop():
    return _loop_thread.get_loop()


def cancel_or_remove_debouncer_task(cache_key):
    task = _loop_debouncer_func_task_cache.get(cache_key, None)
    if not task:
        return
    if task.done():
        del _loop_debouncer_func_task_cache[cache_key]
    else:
        task.cancel()


def run_debouncer_func(cache_key, org, ttl, func, *args, **kwargs):
    cancel_or_remove_debouncer_task(cache_key)
    run_func_partial = functools.partial(_run_func_with_org, cache_key, org, func)

    current = time.time()
    first_run_time = _loop_debouncer_func_task_time_cache.get(cache_key, None)
    if first_run_time is None:
        _loop_debouncer_func_task_time_cache[cache_key] = current
        first_run_time = current

    if current - first_run_time > ttl:
        _loop_debouncer_func_args_cache.pop(cache_key, None)
        _loop_debouncer_func_task_time_cache.pop(cache_key, None)
        executor.submit(run_func_partial, *args, **kwargs)
        logger.debug('pid {} executor submit run {}'.format(
            os.getpid(), func.__name__, ))
        return

    loop = _loop_thread.get_loop()
    _debouncer = Debouncer(run_func_partial, lambda: True, ttl, loop=loop, executor=executor)
    task = asyncio.run_coroutine_threadsafe(_debouncer(*args, **kwargs), loop=loop)
    _loop_debouncer_func_task_cache[cache_key] = task


class Debouncer(object):
    def __init__(self, callback, check, delay, loop=None, executor=None):
        self.callback = callback
        self.check = check
        self.delay = delay
        self.loop = loop
        if not loop:
            self.loop = asyncio.get_event_loop()
        self.executor = executor

    async def __call__(self, *args, **kwargs):
        await asyncio.sleep(self.delay)
        ok = await self._run_sync_to_async(self.check)
        if ok:
            callback_func = functools.partial(self.callback, *args, **kwargs)
            return await self._run_sync_to_async(callback_func)

    async def _run_sync_to_async(self, func):
        if asyncio.iscoroutinefunction(func):
            return await func()
        return await self.loop.run_in_executor(self.executor, func)


ignore_err_exceptions = (
    "(3101, 'Plugin instructed the server to rollback the current transaction.')",
)


def _run_func_with_org(key, org, func, *args, **kwargs):
    from orgs.utils import set_current_org
    try:
        with transaction.atomic():
            set_current_org(org)
            func(*args, **kwargs)
    except Exception as e:
        msg = str(e)
        log_func = logger.error
        if msg in ignore_err_exceptions:
            log_func = logger.info
        pid = os.getpid()
        thread_name = threading.current_thread()
        log_func('pid {} thread {} delay run {} error: {}'.format(
            pid, thread_name, func.__name__, msg))
    _loop_debouncer_func_task_cache.pop(key, None)
    _loop_debouncer_func_args_cache.pop(key, None)
    _loop_debouncer_func_task_time_cache.pop(key, None)


def delay_run(ttl=5, key=None):
    """
    延迟执行函数, 在 ttl 秒内, 只执行最后一次
    :param ttl:
    :param key: 是否合并参数, 一个 callback
    :return:
    """

    def inner(func):
        suffix_key_func = key if key else default_suffix_key
        sigs = inspect.signature(func)
        if len(sigs.parameters) != 0:
            raise ValueError('Merge delay run must not arguments: %s' % func.__name__)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from orgs.utils import get_current_org
            org = get_current_org()
            func_name = f'{func.__module__}_{func.__name__}'
            key_suffix = suffix_key_func(*args)
            cache_key = f'DELAY_RUN_{func_name}_{key_suffix}'
            run_debouncer_func(cache_key, org, ttl, func, *args, **kwargs)

        return wrapper

    return inner


def merge_delay_run(ttl=5, key=None):
    """
    延迟执行函数, 在 ttl 秒内, 只执行最后一次, 并且合并参数
    :param ttl:
    :param key: 是否合并参数, 一个 callback
    :return:
    """

    def delay(func, *args, **kwargs):
        from orgs.utils import get_current_org
        suffix_key_func = key if key else default_suffix_key
        org = get_current_org()
        func_name = f'{func.__module__}_{func.__name__}'
        key_suffix = suffix_key_func(*args, **kwargs)
        cache_key = f'MERGE_DELAY_RUN_{func_name}_{key_suffix}'
        cache_kwargs = _loop_debouncer_func_args_cache.get(cache_key, {})

        for k, v in kwargs.items():
            if not isinstance(v, (tuple, list, set)):
                raise ValueError('func kwargs value must be list or tuple: %s %s' % (func.__name__, v))
            v = set(v)
            if k not in cache_kwargs:
                cache_kwargs[k] = v
            else:
                cache_kwargs[k] = cache_kwargs[k].union(v)
        _loop_debouncer_func_args_cache[cache_key] = cache_kwargs
        run_debouncer_func(cache_key, org, ttl, func, *args, **cache_kwargs)

    def apply(func, sync=False, *args, **kwargs):
        if sync:
            return func(*args, **kwargs)
        else:
            return delay(func, *args, **kwargs)

    def inner(func):
        sigs = inspect.signature(func)
        if len(sigs.parameters) != 1:
            raise ValueError('func must have one arguments: %s' % func.__name__)
        param = list(sigs.parameters.values())[0]
        if not isinstance(param.default, tuple):
            raise ValueError('func default must be tuple: %s' % param.default)
        func.delay = functools.partial(delay, func)
        func.apply = functools.partial(apply, func)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return inner


@delay_run(ttl=5)
def test_delay_run():
    print("Hello,  now is %s" % time.time())


@merge_delay_run(ttl=5, key=lambda users=(): users[0][0])
def test_merge_delay_run(users=()):
    name = ','.join(users)
    time.sleep(2)
    print("Hello, %s, now is %s" % (name, time.time()))


def do_test():
    s = time.time()
    print("start : %s" % time.time())
    for i in range(100):
        # test_delay_run('test', year=i)
        test_merge_delay_run(users=['test %s' % i])
        test_merge_delay_run(users=['best %s' % i])
        test_delay_run('test run %s' % i)

    end = time.time()
    using = end - s
    print("end : %s, using: %s" % (end, using))


def cached_method(ttl=20):
    _cache = {}

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (func, args, tuple(sorted(kwargs.items())))
            # 检查缓存是否存在且未过期
            if key in _cache and time.time() - _cache[key]['timestamp'] < ttl:
                return _cache[key]['result']

            # 缓存过期或不存在，执行方法并缓存结果
            result = func(*args, **kwargs)
            _cache[key] = {'result': result, 'timestamp': time.time()}
            return result

        return wrapper

    return decorator
