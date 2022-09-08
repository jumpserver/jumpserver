from ctypes import *

from .ecc import ECCrefPublicKey, ECCrefPrivateKey, ECCKeyPair
from .exception import PiicoError
from .session_mixin import SM3Mixin, SM4Mixin, SM2Mixin


class Session(SM2Mixin, SM3Mixin, SM4Mixin):
    def __init__(self, driver, session):
        super().__init__()
        self._session = session
        self._driver = driver

    def get_device_info(self):
        pass

    def generate_random(self, length=64):
        random_data = (c_ubyte * length)()
        ret = self._driver.SDF_GenerateRandom(self._session, c_int(length), random_data)
        if ret != 0:
            raise PiicoError("generate random error", ret)
        return bytes(random_data)

    def generate_ecc_key_pair(self, alg_id):
        public_key = ECCrefPublicKey()
        private_key = ECCrefPrivateKey()
        ret = self._driver.SDF_GenerateKeyPair_ECC(self._session, c_int(alg_id), c_int(256), pointer(public_key),
                                                   pointer(private_key))
        if ret != 0:
            raise PiicoError("generate ecc key pair failed", ret)
        return ECCKeyPair(public_key.encode(), private_key.encode())

    def close(self):
        ret = self._driver.SDF_CloseSession(self._session)
        if ret != 0:
            raise PiicoError("close session failed", ret)
