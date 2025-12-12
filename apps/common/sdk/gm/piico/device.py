import os
from ctypes import *

from .exception import PiicoError
from .session import Session
from .cipher import *
from .digest import *
from django.core.cache import cache
from redis_lock import Lock as RedisLock


class Device:
    _driver = None
    __device = None

    def open(self, driver_path="./libpiico_ccmu.so"):
        # load driver
        self.__load_driver(driver_path)
        # open device
        self.__open_device()
        self.__reset_key_store()

    def close(self):
        if self.__device is None:
            raise Exception("device not turned on")
        ret = self._driver.SDF_CloseDevice(self.__device)
        if ret != 0:
            raise Exception("turn off device failed")
        self.__device = None

    def new_session(self):
        session = c_void_p()
        ret = self._driver.SDF_OpenSession(self.__device, pointer(session))
        if ret != 0:
            raise Exception("create session failed")
        return Session(self._driver, session)

    def generate_ecc_key_pair(self):
        session = self.new_session()
        return session.generate_ecc_key_pair(alg_id=0x00020200)

    def generate_random(self, length=64):
        session = self.new_session()
        return session.generate_random(length)

    def new_sm2_ecc_cipher(self, public_key, private_key):
        session = self.new_session()
        return ECCCipher(session, public_key, private_key)

    def new_sm4_ebc_cipher(self, key_val):
        session = self.new_session()
        return EBCCipher(session, key_val)

    def new_sm4_cbc_cipher(self, key_val, iv):
        session = self.new_session()
        return CBCCipher(session, key_val, iv)

    def new_digest(self, mode="sm3"):
        session = self.new_session()
        return Digest(session, mode)

    def __load_driver(self, path):
        # check driver status
        if self._driver is not None:
            raise Exception("already load driver")
        # load driver
        self._driver = cdll.LoadLibrary(path)

    def __open_device(self):
        device = c_void_p()
        ret = self._driver.SDF_OpenDevice(pointer(device))
        if ret != 0:
            raise PiicoError("open piico device failed", ret)
        self.__device = device

    def __reset_key_store(self):
        redis_client = cache.client.get_client()
        server_hostname = os.environ.get("SERVER_HOSTNAME")
        RESET_LOCK_KEY = f"spiico:{server_hostname}:reset"
        LOCK_EXPIRE_SECONDS = 300

        if self._driver is None:
            raise PiicoError("no driver loaded", 0)
        if self.__device is None:
            raise PiicoError("device not open", 0)

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
            raise PiicoError("reset device failed", ret)