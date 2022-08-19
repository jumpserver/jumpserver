import base64

from Cryptodome.Cipher import AES
from gmssl.sm4 import CryptSM4, SM4_ENCRYPT, SM4_DECRYPT
from django.conf import settings


class Encryptor:
    _cache = {}
    '''
    returns the instance in the cache if the parameter digest is consistent.
    '''

    def __new__(cls, *args, **kwargs):
        single_factor_arg_name = ("iv", "key", "alg")
        context = bytes("")
        for arg_name in kwargs.keys():
            if arg_name in single_factor_arg_name:
                val = kwargs[arg_name]
                if val is not None:
                    context += bytes(val)
        digest = hash(context)
        if cls._cache.get(digest, None) is None:
            cls._cache[digest] = super().__new__(cls)
        return cls._cache[digest]

    def encrypt(self, plain_text):
        return base64.urlsafe_b64encode(
            self._encrypt(bytes(plain_text, encoding='utf8'))
        ).decode('utf8')

    def _encrypt(self, plain_text):
        raise NotImplementedError

    def decrypt(self, cipher_text):
        return base64.urlsafe_b64encode(
            self._encrypt(bytes(cipher_text, encoding='utf8'))
        ).decode('utf8')
        pass

    def _decrypt(self, plain_text):
        raise NotImplementedError


class SymmetricEncryptor:

    def __init__(self, key):
        self.key = self.format_key(key)

    @staticmethod
    def format_key(key):
        if not isinstance(key, bytes):
            key = bytes(key, encoding="utf8")
        if len(key) > 32:
            key = key[:32]
        while len(key) % 16 != 0:
            key += b'\0'
        return key


class AESEncryptor(Encryptor, SymmetricEncryptor):
    _alg = {
        "ecb": AES.MODE_ECB,
        "gcm": AES.MODE_GCM,
        "cbc": AES.MODE_CBC,
    }

    def __init__(self, key, iv=None, alg="ecb"):
        super(SymmetricEncryptor, self).__init__(key=key)

        alg = self._alg.get(alg, None) or AES.MODE_ECB
        self.aes_cipher = AES.new(key, alg, iv=iv)

    def _encrypt(self, plain_text):
        return self.aes_cipher.encrypt(plain_text)

    def _decrypt(self, cipher_text):
        return self.aes_cipher.decrypt(cipher_text)


class GMSM4Encryptor(Encryptor, SymmetricEncryptor):
    def __init__(self, key, iv=None, alg="ecb"):
        super(SymmetricEncryptor, self).__init__(key=key)
        self.iv = iv
        self.alg = alg

        self.sm4_encryptor = CryptSM4()
        self.sm4_encryptor.set_key(key, SM4_ENCRYPT)

        self.sm4_decryptor = CryptSM4()
        self.sm4_decryptor.set_key(key, SM4_DECRYPT)

    def get_runner(self, mode):
        target = self.sm4_encryptor if mode == SM4_DECRYPT else self.sm4_decryptor

        def cbc_runner(text):
            return target.crypt_cbc(self.iv, text)

        def ecb_runner(text):
            return target.crypt_ecb(text)

        if self.alg.lower() == "cbc":
            return cbc_runner

        return ecb_runner

    def _encrypt(self, plain_text):
        runner = self.get_runner(SM4_ENCRYPT)
        return runner(plain_text)

    def _decrypt(self, cipher_text):
        runner = self.get_runner(SM4_DECRYPT)
        return runner(cipher_text)


class PiicoSM4Encryptor(Encryptor, SymmetricEncryptor):

    def __init__(self, device, key, iv=None, alg="ecb"):
        super(SymmetricEncryptor, self).__init__(key=key)

    def _encrypt(self, plain_text):
        pass

    def _decrypt(self, plain_text):
        pass


class Crypto:
    default_encrypt = None
    encryptors = {}

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls.init_encryptors()
            return super().__new__(cls)
        return cls._instance

    @classmethod
    def init_encryptors(cls):
        key = settings.SECRET_KEY
        cls.encryptors = {
            "aes": AESEncryptor(key),
            "aes_ecb": AESEncryptor(key),
            "aes_cbc": AESEncryptor(key, alg="cbc"),
            "aes_gcm": AESEncryptor(key, alg="gcm"),
            "gm_sm4": GMSM4Encryptor(key),
            "gm_sm4_ecb": GMSM4Encryptor(key),
            "gm_sm4_cbc": GMSM4Encryptor(key, alg="cbc")
        }
        cryptor_name = settings.SECURITY_DATA_CRYPTO_ALGO if settings.SECURITY_DATA_CRYPTO_ALGO is not None else "aes"
        selected_encrypt = cls.encryptors.pop(cryptor_name, None)
        if selected_encrypt is None:
            raise Exception("unsupported encrypt type {}".format(selected_encrypt))
        cls.default_encrypt = selected_encrypt

    @property
    def encryptor(self):
        return self.default_encrypt

    def encrypt(self, plain_text):
        return self.default_encrypt.encrypt(plain_text)

    def decrypt(self, cipher_text):
        encryptors = [self.default_encrypt, *self.encryptors.values()]
        for decryptor in encryptors:
            try:
                result = decryptor.decrypt(cipher_text)
                if result:
                    return result
            except (TypeError, ValueError, UnicodeDecodeError, IndexError):
                continue
        return ""


crypto = Crypto()
