import os
import base64
from django.conf import settings
from gmssl.sm4 import CryptSM4, SM4_ENCRYPT, SM4_DECRYPT
from gmssl import sm2, sm3, func

from common.sdk.gm import Device
from .base import BaseCrypto, BaseCryptoSuite
from .common import padding_key


class GMSM4EcbCrypto(BaseCrypto):
    def __init__(self, key):
        self.key = padding_key(key, 16)
        self.sm4_encryptor = CryptSM4()
        self.sm4_encryptor.set_key(self.key, SM4_ENCRYPT)

        self.sm4_decryptor = CryptSM4()
        self.sm4_decryptor.set_key(self.key, SM4_DECRYPT)

    def _encrypt(self, data: bytes) -> bytes:
        return self.sm4_encryptor.crypt_ecb(data)

    def _decrypt(self, data: bytes) -> bytes:
        return self.sm4_decryptor.crypt_ecb(data)


class GMDeviceSM4EcbCrypto(BaseCrypto):

    @staticmethod
    def to_16(key):
        while len(key) % 16 != 0:
            key += b'\0'
        return key  # 返回bytes

    def __init__(self, key, device: Device):
        key = padding_key(key, 16)
        self.cipher = device.new_sm4_ebc_cipher(key)

    def _encrypt(self, data: bytes) -> bytes:
        return self.cipher.encrypt(self.to_16(data))

    def _decrypt(self, data: bytes) -> bytes:
        bs = self.cipher.decrypt(data)
        return bs.rstrip(b'\0')


class Sm3Hasher:
    name = 'sm3'
    block_size = 64
    digest_size = 32

    def __init__(self, data):
        self.__data = data

    def hexdigest(self):
        return sm3.sm3_hash(func.bytes_to_list(self.__data))

    def digest(self):
        return bytes.fromhex(self.hexdigest())

    @staticmethod
    def hash(cls, msg=b''):
        return cls(msg)

    def update(self, data):
        self.__data += data

    @classmethod
    def copy(cls, data):
        return cls(data)


class GmCryptoSuite(BaseCryptoSuite):
    crypto = None
    _key = None

    def __init__(self, key, mode: str = 'ecb'):
        self.mode = mode
        if key:
            self.key = key

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, value):
        self._key = value
        self.crypto = GMSM4EcbCrypto(value)

    def encrypt(self, text):
        return self.crypto.encrypt(text)

    def decrypt(self, cipher_text):
        return self.crypto.decrypt(cipher_text)

    def gen_key_pair(self):
        private_key = os.urandom(32).hex()
        sm2_crypt = sm2.CryptSM2(public_key='', private_key=private_key)
        public_key = sm2_crypt._kg(int(private_key, 16), sm2.default_ecc_table['g'])
        return private_key, public_key

    def encrypt_with_key_pair(self, plain_text, public_key):
        sm2_crypt = sm2.CryptSM2(public_key=public_key, private_key='')
        message = sm2_crypt.encrypt(plain_text.encode())
        cipher_text = base64.b64encode(message).decode()
        return cipher_text

    def decrypt_with_key_pair(self, cipher_text, private_key):
        message = base64.b64decode(cipher_text.encode())
        sm2_crypt = sm2.CryptSM2(public_key='', private_key=private_key)
        return sm2_crypt.decrypt(message).decode()

    def hash(self, msg):
        return Sm3Hasher.hash(msg)


def get_gm_sm4_ecb_crypto(key=None):
    key = key or settings.SECRET_KEY
    return GMSM4EcbCrypto(key)


def get_gm_device_sm4_ecb_crypto(device, key=None):
    key = key or settings.SECRET_KEY
    return GMDeviceSM4EcbCrypto(key, device)


def gen_gm_key_pair():
    private_key = os.urandom(32).hex()
    sm2_crypt = sm2.CryptSM2(public_key='', private_key=private_key)
    public_key = sm2_crypt._kg(int(private_key, 16), sm2.default_ecc_table['g'])
    return private_key, public_key


gm_sm4_ecb_crypto = get_gm_sm4_ecb_crypto()
