import os.path
import time
from ctypes import *
from pathlib import Path

import fcntl

from .exception import PiicoError
from .session import Session
from .cipher import *
from .digest import *
from django.conf import settings

RESET_LOCK_FILE = os.path.join(settings.DATA_DIR, "spii_reset.lock")
RESET_DONE_FILE = os.path.join(settings.DATA_DIR, "spii_reset.done")
RESET_EXPIRE_SECONDS = 10


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

        # 1. 确保锁文件存在
        lock_path = Path(RESET_LOCK_FILE)
        lock_path.touch(exist_ok=True)

        with lock_path.open("r+") as lock_f:
            # 2. 阻塞式文件锁，保证进程级互斥
            fcntl.flock(lock_f, fcntl.LOCK_EX)

            try:
                done_path = Path(RESET_DONE_FILE)

                # 3. 判断 reset 是否过期
                if done_path.exists():
                    ts = done_path.stat().st_mtime
                    now = time.time()

                    # 10 秒内已有 reset，直接跳过
                    if (now - ts) < RESET_EXPIRE_SECONDS:
                        return
                    else:
                        # 超时则删除标记文件，重新 reset
                        done_path.unlink(missing_ok=True)

                # 4. 执行 reset
                ret = self._driver.SPII_ResetModule(self.__device)
                if ret != 0:
                    raise PiicoError("reset device failed", ret)

                # 5. 写入新的 reset 时间戳
                done_path.touch(exist_ok=True)

            finally:
                # 6. 释放文件锁
                fcntl.flock(lock_f, fcntl.LOCK_UN)
