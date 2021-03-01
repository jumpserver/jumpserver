from functools import wraps
import threading

from redis_lock import Lock as RedisLock, NotAcquired
from redis import Redis
from django.db import transaction

from common.utils import get_logger
from common.utils.inspect import copy_function_args
from jumpserver.const import CONFIG
from common.local import thread_local

logger = get_logger(__file__)


class AcquireFailed(RuntimeError):
    pass


class LockHasTimeOut(RuntimeError):
    pass


class DistributedLock(RedisLock):
    def __init__(self, name, *, expire=None, release_on_transaction_commit=False,
                 reentrant=False, release_raise_exc=False, auto_renewal_seconds=60):
        """
        使用 redis 构造的分布式锁

        :param name:
            锁的名字，要全局唯一
        :param expire:
            锁的过期时间
        :param release_on_transaction_commit:
            是否在当前事务结束后再释放锁
        :param release_raise_exc:
            释放锁时，如果没有持有锁是否抛异常或静默
        :param auto_renewal_seconds:
            当持有一个无限期锁的时候，刷新锁的时间，具体参考 `redis_lock.Lock#auto_renewal`
        :param reentrant:
            是否可重入
        """
        self.kwargs_copy = copy_function_args(self.__init__, locals())
        redis = Redis(host=CONFIG.REDIS_HOST, port=CONFIG.REDIS_PORT, password=CONFIG.REDIS_PASSWORD)

        if expire is None:
            expire = auto_renewal_seconds
            auto_renewal = True
        else:
            auto_renewal = False

        super().__init__(redis_client=redis, name=name, expire=expire, auto_renewal=auto_renewal)
        self._release_on_transaction_commit = release_on_transaction_commit
        self._release_raise_exc = release_raise_exc
        self._reentrant = reentrant
        self._acquired_reentrant_lock = False
        self._thread_id = threading.current_thread().ident

    def __enter__(self):
        acquired = self.acquire(blocking=True)
        if not acquired:
            raise AcquireFailed
        return self

    def __exit__(self, exc_type=None, exc_value=None, traceback=None):
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

    def locked_by_current_thread(self):
        if self.locked():
            owner_id = self.get_owner_id()
            local_owner_id = getattr(thread_local, self.name, None)

            if local_owner_id and owner_id == local_owner_id:
                return True
        return False

    def acquire(self, blocking=True, timeout=None):
        if self._reentrant:
            if self.locked_by_current_thread():
                self._acquired_reentrant_lock = True
                logger.debug(
                    f'I[{self.id}] reentry lock[{self.name}] in thread[{self._thread_id}].')
                return True

            logger.debug(f'I[{self.id}] attempt acquire reentrant-lock[{self.name}].')
            acquired = super().acquire(blocking=blocking, timeout=timeout)
            if acquired:
                logger.debug(f'I[{self.id}] acquired reentrant-lock[{self.name}] now.')
                setattr(thread_local, self.name, self.id)
            else:
                logger.debug(f'I[{self.id}] acquired reentrant-lock[{self.name}] failed.')
            return acquired
        else:
            logger.debug(f'I[{self.id}] attempt acquire lock[{self.name}].')
            acquired = super().acquire(blocking=blocking, timeout=timeout)
            logger.debug(f'I[{self.id}] acquired lock[{self.name}] {acquired}.')
            return acquired

    @property
    def name(self):
        return self._name

    def _raise_exc_with_log(self, msg, *, exc_cls=NotAcquired):
        e = exc_cls(msg)
        logger.error(msg)
        self._raise_exc(e)

    def _raise_exc(self, e):
        if self._release_raise_exc:
            raise e

    def _release_on_reentrant_locked_by_brother(self):
        if self._acquired_reentrant_lock:
            self._acquired_reentrant_lock = False
            logger.debug(f'I[{self.id}] released reentrant-lock[{self.name}] owner[{self.get_owner_id()}] in thread[{self._thread_id}]')
            return
        else:
            self._raise_exc_with_log(f'Reentrant-lock[{self.name}] is not acquired by me[{self.id}].')

    def _release_on_reentrant_locked_by_me(self):
        logger.debug(f'I[{self.id}] release reentrant-lock[{self.name}] in thread[{self._thread_id}]')

        id = getattr(thread_local, self.name, None)
        if id != self.id:
            raise PermissionError(f'Reentrant-lock[{self.name}] is not locked by me[{self.id}], owner[{id}]')
        try:
            # 这里要保证先删除 thread_local 的标记，
            delattr(thread_local, self.name)
        except AttributeError:
            pass
        finally:
            try:
                # 这里处理的是边界情况，
                # 判断锁是我的 -> 锁超时 -> 释放锁报错
                # 此时的报错应该被静默
                self._release_redis_lock()
            except NotAcquired:
                pass

    def _release_redis_lock(self):
        # 最底层 api
        super().release()

    def _release(self):
        try:
            self._release_redis_lock()
            logger.debug(f'I[{self.id}] released lock[{self.name}]')
        except NotAcquired as e:
            logger.error(f'I[{self.id}] release lock[{self.name}] failed {e}')
            self._raise_exc(e)

    def release(self):
        _release = self._release

        # 处理可重入锁
        if self._reentrant:
            if self.locked_by_current_thread():
                if self.locked_by_me():
                    _release = self._release_on_reentrant_locked_by_me
                else:
                    _release = self._release_on_reentrant_locked_by_brother
            else:
                self._raise_exc_with_log(f'Reentrant-lock[{self.name}] is not acquired in current-thread[{self._thread_id}]')

        # 处理是否在事务提交时才释放锁
        if self._release_on_transaction_commit:
            logger.debug(f'I[{self.id}] release lock[{self.name}] on transaction commit ...')
            transaction.on_commit(_release)
        else:
            _release()
