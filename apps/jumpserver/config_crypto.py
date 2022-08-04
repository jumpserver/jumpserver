import base64
from gmssl.sm4 import CryptSM4, SM4_ENCRYPT, SM4_DECRYPT


class ConfigCrypto(object):
    def __init__(self, key):
        self.safe_key = self.process_key(key)
        self.sm4_encryptor = CryptSM4()
        self.sm4_encryptor.set_key(self.safe_key, SM4_ENCRYPT)

        self.sm4_decryptor = CryptSM4()
        self.sm4_decryptor.set_key(self.safe_key, SM4_DECRYPT)

    @staticmethod
    def process_key(secret_encrypt_key):
        key = secret_encrypt_key.encode()
        if len(key) >= 16:
            key = key[:16]
        else:
            key += b'\0' * (16 - len(key))
        return key

    def encrypt(self, data):
        data = bytes(data, encoding='utf8')
        return base64.b64encode(self.sm4_encryptor.crypt_ecb(data)).decode('utf8')

    def decrypt(self, data):
        data = base64.urlsafe_b64decode(bytes(data, encoding='utf8'))
        return self.sm4_decryptor.crypt_ecb(data).decode('utf8')
