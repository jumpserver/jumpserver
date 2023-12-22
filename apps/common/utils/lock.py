import threading
from functools import wraps

from django.db import transaction
from redis_lock import (
    Lock as RedisLock, NotAcquired, UNLOCK_SCRIPT,
    EXTEND_SCRIPT, RESET_SCRIPT, RESET_ALL_SCRIPT
)

from common.local import thread_local
from common.utils import get_logger
from common.utils.connection import get_redis_client
from common.utils.inspect import copy_function_args

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
        redis = get_redis_client()

        if expire is None:
            expire = auto_renewal_seconds
            auto_renewal = True
        else:
            auto_renewal = False

        super().__init__(redis_client=redis, name='{' + name + '}', expire=expire, auto_renewal=auto_renewal)
        self.register_scripts(redis)
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

    @classmethod
    def register_scripts(cls, redis_client):
        cls.unlock_script = redis_client.register_script(UNLOCK_SCRIPT)
        cls.extend_script = redis_client.register_script(EXTEND_SCRIPT)
        cls.reset_script = redis_client.register_script(RESET_SCRIPT)
        cls.reset_all_script = redis_client.register_script(RESET_ALL_SCRIPT)

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
                logger.debug(f'Reentry lock ok: lock_id={self.id} owner_id={self.get_owner_id()} lock={self.name}')
                return True

            logger.debug(f'Attempt acquire reentrant-lock: lock_id={self.id} lock={self.name}')
            acquired = super().acquire(blocking=blocking, timeout=timeout)
            if acquired:
                logger.debug(f'Acquired reentrant-lock ok: lock_id={self.id} lock={self.name}')
                setattr(thread_local, self.name, self.id)
            else:
                logger.debug(f'Acquired reentrant-lock failed: lock_id={self.id} lock={self.name}')
            return acquired
        else:
            logger.debug(f'Attempt acquire lock: lock_id={self.id} lock={self.name}')
            acquired = super().acquire(blocking=blocking, timeout=timeout)
            logger.debug(f'Acquired lock: ok={acquired} lock_id={self.id} lock={self.name}')
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
            logger.debug(f'Released reentrant-lock: lock_id={self.id} owner_id={self.get_owner_id()} lock={self.name}')
            return
        else:
            self._raise_exc_with_log(
                f'Reentrant-lock is not acquired: lock_id={self.id} owner_id={self.get_owner_id()} lock={self.name}')

    def _release_on_reentrant_locked_by_me(self):
        logger.debug(f'Release reentrant-lock locked by me: lock_id={self.id} lock={self.name}')

        id = getattr(thread_local, self.name, None)
        if id != self.id:
            raise PermissionError(
                f'Reentrant-lock is not locked by me: lock_id={self.id} owner_id={self.get_owner_id()} lock={self.name}')
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
            logger.debug(f'Released lock: lock_id={self.id} lock={self.name}')
        except NotAcquired as e:
            logger.error(f'Release lock failed: lock_id={self.id} lock={self.name} error: {e}')
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
                self._raise_exc_with_log(
                    f'Reentrant-lock is not acquired: lock_id={self.id} lock={self.name}')

        # 处理是否在事务提交时才释放锁
        if self._release_on_transaction_commit:
            logger.debug(
                f'Release lock on transaction commit:lock_id={self.id} lock={self.name}')
            transaction.on_commit(_release)
        else:
            _release()
