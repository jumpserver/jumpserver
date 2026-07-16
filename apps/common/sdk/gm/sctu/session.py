from ctypes import *

from common.sdk.gm.base.exception import GMDeviceError
from .session_mixin import SM4Mixin


class Session(SM4Mixin):
    def __init__(self, driver, session):
        super().__init__()
        self._session = session
        self._driver = driver

    def get_device_info(self):
        pass

    def generate_random(self, length=64):
        random_data = (c_ubyte * length)()
        ret = self._driver.HS_SDF_GenerateRandom(self._session, c_int(length), random_data)
        if ret != 0:
            raise GMDeviceError("generate random error", ret)
        return bytes(random_data)

    def close(self):
        ret = self._driver.HS_SDF_CloseSession(self._session)
        if ret != 0:
            raise GMDeviceError("close session failed", ret)
