from functools import wraps
import threading

from redis_lock import Lock as RedisLock, NotAcquired
from redis import Redis
from django.db import transaction

from common.utils import get_logger
from common.utils.inspect import copy_function_args
from apps.jumpserver.const import CONFIG

logger = get_logger(__file__)


class AcquireFailed(RuntimeError):
    pass


class DistributedLock(RedisLock):
    def __init__(self, name, blocking=True, expire=None, release_lock_on_transaction_commit=False,
                 release_raise_exc=False, auto_renewal_seconds=60*2):
        """
        使用 redis 构造的分布式锁

        :param name:
            锁的名字，要全局唯一
        :param blocking:
            该参数只在锁作为装饰器或者 `with` 时有效。
        :param expire:
            锁的过期时间
        :param release_lock_on_transaction_commit:
            是否在当前事务结束后再释放锁
        :param release_raise_exc:
            释放锁时，如果没有持有锁是否抛异常或静默
        :param auto_renewal_seconds:
            当持有一个无限期锁的时候，刷新锁的时间，具体参考 `redis_lock.Lock#auto_renewal`
        """
        self.kwargs_copy = copy_function_args(self.__init__, locals())
        redis = Redis(host=CONFIG.REDIS_HOST, port=CONFIG.REDIS_PORT, password=CONFIG.REDIS_PASSWORD)

        if expire is None:
            expire = auto_renewal_seconds
            auto_renewal = True
        else:
            auto_renewal = False

        super().__init__(redis_client=redis, name=name, expire=expire, auto_renewal=auto_renewal)
        self._blocking = blocking
        self._release_lock_on_transaction_commit = release_lock_on_transaction_commit
        self._release_raise_exc = release_raise_exc

    def __enter__(self):
        thread_id = threading.current_thread().ident
        logger.debug(f'Attempt to acquire global lock: thread {thread_id} lock {self._name}')
        acquired = self.acquire(blocking=self._blocking)
        if self._blocking and not acquired:
            logger.debug(f'Not acquired lock, but blocking=True, thread {thread_id} lock {self._name}')
            raise EnvironmentError("Lock wasn't acquired, but blocking=True")
        if not acquired:
            logger.debug(f'Not acquired the lock, thread {thread_id} lock {self._name}')
            raise AcquireFailed
        logger.debug(f'Acquire lock success, thread {thread_id} lock {self._name}')
        return self

    def __exit__(self, exc_type=None, exc_value=None, traceback=None):
        if self._release_lock_on_transaction_commit:
            transaction.on_commit(self.release)
        else:
            self.release()

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwds):
            # 要创建一个新的锁对象
            with self.__class__(**self.kwargs_copy):
                return func(*args, **kwds)
        return inner

    def locked_by_me(self):
        if self.locked():
            if self.get_owner_id() == self.id:
                return True
        return False

    def release(self):
        try:
            super().release()
        except AcquireFailed as e:
            if self._release_raise_exc:
                raise e
