from ctypes import *

from Cryptodome.Util.asn1 import DerSequence
from .ecc import ECCrefPublicKey, ECCrefPrivateKey, ECCKeyPair, ECCSignature
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
        ret = self._driver.SDF_GenerateKeyPair_ECC(
            self._session,
            c_int(alg_id),
            c_int(256),
            pointer(public_key),
            pointer(private_key),
        )
        if ret != 0:
            raise PiicoError("generate ecc key pair failed", ret)
        return ECCKeyPair(public_key.encode(), private_key.encode())

    def verify_sign_ecc(self, alg_id, public_key, raw_data, sign_data):
        pos = 0
        k1 = bytes([0] * 32) + bytes(public_key[pos : pos + 32])
        pos += 32
        k2 = bytes([0] * 32) + bytes(public_key[pos : pos + 32])
        pk = ECCrefPublicKey(
            c_uint(0x100), (c_ubyte * len(k1))(*k1), (c_ubyte * len(k2))(*k2)
        )

        seq_der = DerSequence()
        decoded_sign = seq_der.decode(sign_data)
        if decoded_sign and len(decoded_sign) != 2:
            raise PiicoError("verify_sign decoded_sign", -1)
        r = bytes([0] * 32) + int(decoded_sign[0]).to_bytes(32, byteorder="big")
        s = bytes([0] * 32) + int(decoded_sign[1]).to_bytes(32, byteorder="big")
        signature = ECCSignature((c_ubyte * len(r))(*r), (c_ubyte * len(s))(*s))

        plain_text = (c_ubyte * len(raw_data))(*raw_data)
        ret = self._driver.SDF_ExternalVerify_ECC(
            self._session,
            c_int(alg_id),
            pointer(pk),
            plain_text,
            c_int(len(plain_text)),
            pointer(signature),
        )
        if ret != 0:
            raise PiicoError("verify_sign", ret)
        return True

    def close(self):
        ret = self._driver.SDF_CloseSession(self._session)
        if ret != 0:
            raise PiicoError("close session failed", ret)
