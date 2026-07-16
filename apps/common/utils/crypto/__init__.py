from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from common.sdk.gm import open_gm_device, CryptoVendor

from .common import *
from .session import *
from .rsa_aes import *
from .gm import *


class Crypto:
    cryptor_map = {
        'aes_ecb': aes_ecb_crypto,
        'aes_gcm': aes_crypto,
        'aes': aes_crypto,
        'gm_sm4_ecb': gm_sm4_ecb_crypto,
        'gm': gm_sm4_ecb_crypto,
    }
    cryptos = []

    def __init__(self):
        crypt_algo = settings.SECURITY_DATA_CRYPTO_ALGO
        if not crypt_algo:
            if settings.GM_DEVICE_ENABLE:
                crypto, crypt_algo = self.get_gm_device_crypto()
                self.cryptor_map[crypt_algo] = crypto
            else:
                crypt_algo = 'aes'
        cryptor = self.cryptor_map.get(crypt_algo, None)
        if cryptor is None:
            raise ImproperlyConfigured(
                f'Crypto method not supported {settings.SECURITY_DATA_CRYPTO_ALGO}'
            )
        others = set(self.cryptor_map.values()) - {cryptor}
        self.cryptos = [cryptor, *others]

    def get_gm_crypto(self):
        if settings.GM_DEVICE_ENABLE:
            crypto, crypt_algo = self.get_gm_device_crypto()
            self.cryptor_map[crypt_algo] = crypto
        else:
            crypt_algo = 'gm'

    def get_gm_device_crypto(self):
        vendor = CryptoVendor.from_str(settings.GM_VENDOR_NAME)
        device = open_gm_device(vendor)
        crypto = get_gm_device_sm4_ecb_crypto(device)
        return crypto, 'gm_device'

    @property
    def encryptor(self):
        return self.cryptos[0]

    def encrypt(self, text):
        if text is None:
            return text
        return self.encryptor.encrypt(text)

    def decrypt(self, text):
        for i, cryptor in enumerate(self.cryptos):
            try:
                origin_text = cryptor.decrypt(text)
                if i == 0:
                    return origin_text
                if origin_text:
                    # 有时不同算法解密不报错，但是返回空字符串
                    return origin_text
            except Exception:
                continue


crypto = Crypto()
