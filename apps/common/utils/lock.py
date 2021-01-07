from functools import wraps
import threading

from redis_lock import Lock as RedisLock
from redis import Redis

from common.utils import get_logger
from common.utils.inspect import copy_function_args
from apps.jumpserver.const import CONFIG

logger = get_logger(__file__)


class AcquireFailed(RuntimeError):
    pass


class DistributedLock(RedisLock):
    def __init__(self, name, blocking=True, expire=60*2, auto_renewal=True):
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

    def __enter__(self):
        thread_id = threading.current_thread().ident
        logger.debug(f'DISTRIBUTED_LOCK: <thread_id:{thread_id}> attempt to acquire <lock:{self._name}> ...')
        acquired = self.acquire(blocking=self._blocking)
        if self._blocking and not acquired:
            logger.debug(f'DISTRIBUTED_LOCK: <thread_id:{thread_id}> was not acquired <lock:{self._name}>, but blocking=True')
            raise EnvironmentError("Lock wasn't acquired, but blocking=True")
        if not acquired:
            logger.debug(f'DISTRIBUTED_LOCK: <thread_id:{thread_id}> acquire <lock:{self._name}> failed')
            raise AcquireFailed
        logger.debug(f'DISTRIBUTED_LOCK: <thread_id:{thread_id}> acquire <lock:{self._name}> ok')
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
