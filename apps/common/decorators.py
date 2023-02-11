# -*- coding: utf-8 -*-
#
import asyncio
import functools
import inspect
import threading
import time
from concurrent.futures import ThreadPoolExecutor

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
_loop_thread.setDaemon(True)
_loop_thread.start()
executor = ThreadPoolExecutor(max_workers=10,
                              thread_name_prefix='debouncer')
_loop_debouncer_func_task_cache = {}
_loop_debouncer_func_args_cache = {}


def cancel_or_remove_debouncer_task(cache_key):
    task = _loop_debouncer_func_task_cache.get(cache_key, None)
    if not task:
        return
    if task.done():
        del _loop_debouncer_func_task_cache[cache_key]
    else:
        task.cancel()


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


def _run_func_with_org(key, org, func, *args, **kwargs):
    from orgs.utils import set_current_org
    try:
        set_current_org(org)
        func(*args, **kwargs)
    except Exception as e:
        logger.error('delay run error: %s' % e)
    _loop_debouncer_func_task_cache.pop(key, None)
    _loop_debouncer_func_args_cache.pop(key, None)


def delay_run(ttl=5, key=None, merge_args=False):
    """
    延迟执行函数, 在 ttl 秒内, 只执行最后一次
    :param ttl:
    :param key: 是否合并参数, 一个 callback
    :param merge_args: 是否合并之前的参数, bool
    :return:
    """

    def inner(func):
        sigs = inspect.signature(func)
        if len(sigs.parameters) != 1:
            raise ValueError('func must have one arguments: %s' % func.__name__)
        param = list(sigs.parameters.values())[0]
        if not str(param).startswith('*') or param.kind == param.VAR_KEYWORD:
            raise ValueError('func args must be startswith *: %s and not have **kwargs ' % func.__name__)
        suffix_key_func = key if key else default_suffix_key

        @functools.wraps(func)
        def wrapper(*args):
            from orgs.utils import get_current_org
            org = get_current_org()
            func_name = f'{func.__module__}_{func.__name__}'
            key_suffix = suffix_key_func(*args)
            cache_key = f'DELAY_RUN_{func_name}_{key_suffix}'
            new_arg = args
            if merge_args:
                values = _loop_debouncer_func_args_cache.get(cache_key, [])
                new_arg = [*values, *args]
                _loop_debouncer_func_args_cache[cache_key] = new_arg

            cancel_or_remove_debouncer_task(cache_key)

            run_func_partial = functools.partial(_run_func_with_org, cache_key, org, func)
            loop = _loop_thread.get_loop()
            _debouncer = Debouncer(run_func_partial, lambda: True, ttl,
                                   loop=loop, executor=executor)
            task = asyncio.run_coroutine_threadsafe(_debouncer(*new_arg),
                                                    loop=loop)
            _loop_debouncer_func_task_cache[cache_key] = task

        return wrapper

    return inner


merge_delay_run = functools.partial(delay_run, merge_args=True)


@delay_run(ttl=5)
def test_delay_run(*username):
    print("Hello, %s, now is %s" % (username, time.time()))


@delay_run(ttl=5, key=lambda *users: users[0][0], merge_args=True)
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
        test_delay_run('test run %s' % i)

    end = time.time()
    using = end - s
    print("end : %s, using: %s" % (end, using))
