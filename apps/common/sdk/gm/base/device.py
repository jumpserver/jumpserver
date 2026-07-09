import base64
from ctypes import *
from .session import Session
from .cipher import *
from .digest import *
from .const import SGD_SM2
from django.conf import settings


class Device:
    _driver = None
    __device = None
    name = None

    def open(self, driver_path):
        if self.__device is not None:
            return

        # 如果设置里指定了 要覆盖
        if settings.GM_DRIVER_PATH:
            driver_path = settings.GM_DRIVER_PATH

        self.__load_driver(driver_path)
        # open device
        self.__open_device()
        self.reset_key_store()

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

    def verify_sign(self, public_key, raw_data, sign_data):
        session = self.new_session()
        return session.verify_sign_ecc(
            SGD_SM2,
            base64.b64decode(public_key),
            base64.b64decode(raw_data),
            base64.b64decode(sign_data),
        )

    def sm3_hmac(self, key, data):
        session = self.new_session()
        return session.sm3_hmac(key, data)

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
            raise Exception("open {} device failed".format(self.name), ret)
        self.__device = device

    def reset_key_store(self):
        pass
