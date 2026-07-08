from ctypes import *

from ..base.device import Device
from .session import Session
from .cipher import EBCCipher


class SCTUDevice(Device):
    name = "sctu"

    def __init__(self):
        self.open("libhsctu_guomi_vpn.so")

    def open(self, driver_path):
        # load driver
        self.__load_driver(driver_path)
        # open device
        self.__open_device()

    def __load_driver(self, path):
        # check driver status
        if self._driver is not None:
            raise Exception("already load driver")
        # load driver
        self._driver = cdll.LoadLibrary(path)

    def __open_device(self):
        device = c_void_p()
        ret = self._driver.HS_SDF_OpenDevice(pointer(device))
        if ret != 0:
            raise Exception("open {} device failed".format(self.name), ret)
        self.__device = device

    def new_session(self):
        session = c_void_p()
        ret = self._driver.HS_SDF_OpenSession(self.__device, pointer(session))
        if ret != 0:
            raise Exception("create session failed")
        return Session(self._driver, session)

    def new_sm4_ebc_cipher(self, key_val):
        session = self.new_session()
        return EBCCipher(session, key_val)

    def close(self):
        if self.__device is None:
            raise Exception("device not turned on")
        ret = self._driver.HS_SDF_CloseDevice(self.__device)
        if ret != 0:
            raise Exception("turn off device failed")
        self.__device = None