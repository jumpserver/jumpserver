from functools import wraps
import threading

from redis_lock import Lock as RedisLock
from redis import Redis
from django.db import transaction

from common.utils import get_logger
from common.utils.inspect import copy_function_args
from apps.jumpserver.const import CONFIG
from orgs.utils import current_org
from common.local import thread_local

logger = get_logger(__file__)


class AcquireFailed(RuntimeError):
    pass


class DistributedLock(RedisLock):
    def __init__(self, name, blocking=True, expire=60*2, auto_renewal=True,
                 release_lock_on_transaction_commit=False, current_thread_reentrant=False):
        """
        使用 redis 构造的分布式锁

        :param name:
            锁的名字，要全局唯一
        :param blocking:
            该参数只在锁作为装饰器或者 `with` 时有效。
        :param expire:
            锁的过期时间，注意不一定是锁到这个时间就释放了，分两种情况
            当 `auto_renewal=False` 时，锁会释放
            当 `auto_renewal=True` 时，如果过期之前程序还没释放锁，我们会延长锁的存活时间。
            这里的作用是防止程序意外终止没有释放锁，导致死锁。
        """
        self.kwargs_copy = copy_function_args(self.__init__, locals())
        redis = Redis(host=CONFIG.REDIS_HOST, port=CONFIG.REDIS_PORT, password=CONFIG.REDIS_PASSWORD)
        super().__init__(redis_client=redis, name=name, expire=expire, auto_renewal=auto_renewal)
        self._blocking = blocking
        self._release_lock_on_transaction_commit = release_lock_on_transaction_commit
        self._current_thread_reentrant = current_thread_reentrant

    def __enter__(self):
        acquired = self.acquire(blocking=self._blocking)
        if self._blocking and not acquired:
            raise EnvironmentError("Lock wasn't acquired, but blocking=True")
        if not acquired:
            raise AcquireFailed
        return self

    def __exit__(self, exc_type=None, exc_value=None, traceback=None):
        self.release()

    def locked_by_me(self):
        if self.locked():
            if self.get_owner_id() == self.id:
                return True
        return False

    def locked_by_current_thread(self):
        if self.locked():
            id = getattr(thread_local, self.name, '')
            if id:
                return True
        return False

    def acquire(self, blocking=True, timeout=None):
        thread_id = threading.current_thread().ident
        if self._current_thread_reentrant:
            if self.locked_by_current_thread():
                logger.debug(f'I[{self.id}] acquire current thread reentrant lock[{self.name}], already locked by current thread[{thread_id}] lock[{self.get_owner_id()}].')
                return True

            logger.debug(f'I[{self.id}] attempt acquire current thread[{thread_id}] reentrant lock[{self.name}].')
            acquired = super().acquire(blocking=blocking, timeout=timeout)
            if acquired:
                logger.debug(f'I[{self.id}] acquired current thread[{thread_id}] reentrant lock[{self.name}] now.')
                setattr(thread_local, self.name, self.id)
            else:
                logger.debug(f'I[{self.id}] acquired current thread[{thread_id}] reentrant lock[{self.name}] failed.')
            return acquired
        else:
            logger.debug(f'I[{self.id}] attempt acquire lock[{self.name}] in thread[{thread_id}].')
            acquired = super().acquire(blocking=blocking, timeout=timeout)
            logger.debug(f'I[{self.id}] acquired lock[{self.name}] in thread[{thread_id}] {acquired}.')
            return acquired

    def _release_on_current_thread_reentrant(self):
        thread_id = threading.current_thread().ident
        logger.debug(f'I[{self.id}] release current thread[{thread_id}] reentrant lock[{self.name}]')
        id = getattr(thread_local, self.name, '')
        if id != self.id:
            raise ValueError(f'I[{self.id}] acquired a current thread[{thread_id}] reentrant lock[{self.name}], but `owner[{id}]` in thread_local is not me, i can release it')
        try:
            delattr(thread_local, self.name)
        except AttributeError:
            pass
        self._release()

    def _release(self):
        thread_id = threading.current_thread().ident
        logger.debug(f'I[{self.id}] release lock[{self.name}] in thread[{thread_id}]')
        super().release()

    def release(self):
        _release = self._release

        # 处理可重入锁
        if self._current_thread_reentrant:
            if self.locked_by_me():
                _release = self._release_on_current_thread_reentrant
            else:
                logger.debug(f'Release current thread reentrant lock[{self.name}], locked by current thread lock[{self.get_owner_id()}], i[{self.id}] pass')
                return

        # 处理是否在事务提交时才释放锁
        if self._release_lock_on_transaction_commit:
            logger.debug(f'Release lock[{self.name}] by me[{self.id}] on transaction commit, wait transaction...')
            transaction.on_commit(_release)
        else:
            _release()

    @property
    def name(self):
        return self._name

    def __call__(self, func):
        @wraps(func)
        def inner(*args, **kwds):
            # 要创建一个新的锁对象
            with self.__class__(**self.kwargs_copy):
                return func(*args, **kwds)

        return inner
