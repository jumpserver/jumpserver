import base64
import os
from ctypes import *

from django.core.cache import cache
from redis_lock import Lock as RedisLock

from common.utils import get_logger
from .cipher import *
from .const import SGD_SM2
from .digest import *
from .exception import PiicoError
from .session import Session

logger = get_logger(__file__)


class Device:
    _driver = None
    __device = None

    def open(self, driver_path="./libpiico_ccmu.so"):
        if self.__device is not None:
            return
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
        return session.generate_ecc_key_pair(alg_id=SGD_SM2)

    def generate_random(self, length=64):
        session = self.new_session()
        return session.generate_random(length)

    def verify_sign(self, public_key, raw_data, sign_data):
        logger.debug("verify_sign public_key: %s", public_key)
        logger.debug("verify_sign raw_data: %s", raw_data)
        logger.debug("verify_sign sign_data: %s", sign_data)
        session = self.new_session()
        return session.verify_sign_ecc(
            SGD_SM2,
            base64.b64decode(public_key),
            base64.b64decode(raw_data),
            base64.b64decode(sign_data),
        )

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

    def sm3_hmac(self, key, data):
        session = self.new_session()
        return session.sm3_hmac(key, data)

    def __load_driver(self, path):
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
        logger.debug("SPII_ResetModule")
        ret = self._driver.SPII_ResetModule(self.__device)
        if ret != 0:
            raise PiicoError("reset device failed", ret)
