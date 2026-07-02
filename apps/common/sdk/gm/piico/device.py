import os
from ..base.device import Device
from django.core.cache import cache
from redis_lock import Lock as RedisLock


class PiicoDevice(Device):
    name = "piico"

    def __init__(self):
        self.open()

    # 默认去lib路径检索
    def open(self, driver_path="libpiico_ccmu.so"):
        super().open(driver_path)

    def reset_key_store(self):
        redis_client = cache.client.get_client()
        server_hostname = os.environ.get("SERVER_HOSTNAME")
        RESET_LOCK_KEY = f"spiico:{server_hostname}:reset"
        LOCK_EXPIRE_SECONDS = 300

        if self._driver is None:
            raise Exception("no driver loaded", 0)
        if self.__device is None:
            raise Exception("device not open", 0)

        # ---- 分布式锁（Redis-Lock 实现 Redlock） ----
        lock = RedisLock(
            redis_client,
            RESET_LOCK_KEY,
            expire=LOCK_EXPIRE_SECONDS,  # 锁自动过期
            auto_renewal=False,  # 不自动续租
        )

        # 尝试获取锁，拿不到直接返回
        if not lock.acquire(blocking=False):
            return
            # ---- 真正执行 reset ----
        ret = self._driver.SPII_ResetModule(self.__device)
        if ret != 0:
            raise Exception("reset device failed", ret)
