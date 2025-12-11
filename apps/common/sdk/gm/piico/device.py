import os.path
import time
from ctypes import *

from .exception import PiicoError
from .session import Session
from .cipher import *
from .digest import *
from django.conf import settings
from django.core.cache import cache

RESET_LOCK_KEY = "spiico:reset:lock"
RESET_TS_KEY = "spiico:reset:ts"
RESET_EXPIRE_SECONDS = 10  # reset 结果的有效期（你要的 10 秒）
LOCK_TIMEOUT_SECONDS = 30  # 锁的超时时间（防止拿了锁崩掉一直不释放）
WAIT_INTERVAL = 0.2  # 等待锁时的轮询间隔
WAIT_MAX_SECONDS = 15  # 最多等多久别人 reset 完成


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
    if self._driver is None:
        raise PiicoError("no driver loaded", 0)
    if self.__device is None:
        raise PiicoError("device not open", 0)

    now = time.time()

    # 1. 快速路径：先看最近一次 reset 是否在 10 秒内
    last_ts = cache.get(RESET_TS_KEY)
    if last_ts is not None and (now - float(last_ts)) < RESET_EXPIRE_SECONDS:
        # 10 秒内已经有进程 reset 过了，直接跳过
        return

    # 2. 尝试获取分布式锁
    start_wait = time.time()
    while True:
        # cache.add 是原子操作，只有第一个成功的人拿到锁
        got_lock = cache.add(RESET_LOCK_KEY, "1", timeout=LOCK_TIMEOUT_SECONDS)
        if got_lock:
            # 拿到锁的进程负责真正检查 + 执行 reset
            break

        # 没拿到锁，说明别人正在 reset，我们等它完成
        # 等的过程中如果发现已经有人 reset 完成且在有效期内，直接返回
        last_ts = cache.get(RESET_TS_KEY)
        now = time.time()
        if last_ts is not None and (now - float(last_ts)) < RESET_EXPIRE_SECONDS:
            return

        if now - start_wait > WAIT_MAX_SECONDS:
            # 等太久了，认为有问题（锁卡死/其他异常）
            raise PiicoError("wait reset lock timeout", 0)

        time.sleep(WAIT_INTERVAL)

    # 3. 当前进程已经持有锁，双重检查（期间可能有别的进程先抢到锁并完成了 reset）
    try:
        now = time.time()
        last_ts = cache.get(RESET_TS_KEY)
        if last_ts is not None and (now - float(last_ts)) < RESET_EXPIRE_SECONDS:
            # 在我们拿锁之前，可能已经有人 reset 过且在有效期内，直接跳过
            return

        # 4. 真正执行 reset
        ret = self._driver.SPII_ResetModule(self.__device)
        if ret != 0:
            raise PiicoError("reset device failed", ret)

        # 5. 记录这次 reset 的时间戳（不设过期，让逻辑自己判断 10 秒）
        cache.set(RESET_TS_KEY, str(time.time()), None)

    finally:
        # 6. 无论成功失败都要释放锁，避免死锁
        cache.delete(RESET_LOCK_KEY)
