from .const import CIPHER_ALG_ID, SGD_SM2_3


class ECCCipher:
    def __init__(self, session, public_key, private_key):
        self._session = session
        self.public_key = public_key
        self.private_key = private_key

    def encrypt(self, plain_text):
        return self._session.ecc_encrypt(self.public_key, plain_text, SGD_SM2_3)

    def decrypt(self, cipher_text):
        return self._session.ecc_decrypt(self.private_key, cipher_text, SGD_SM2_3)


class EBCCipher:

    def __init__(self, session, key_val):
        self._session = session
        self._key = key_val if isinstance(key_val, bytes) else bytes(key_val, encoding='utf-8')
        self._alg = "sm4_ebc"
        self._iv = None

    @staticmethod
    def __padding(data):
        if not isinstance(data, bytes):
            data = bytes(data, encoding='utf-8')
        while len(data) == 0 or len(data) % 16 != 0:
            data += b'\0'
        return data

    def encrypt(self, plain_text):
        plain_text = self.__padding(plain_text)
        cipher_text = self._session.encrypt(plain_text, self._key, CIPHER_ALG_ID[self._alg], self._iv)
        return bytes(cipher_text)

    def decrypt(self, cipher_text):
        plain_text = self._session.decrypt(cipher_text, self._key, CIPHER_ALG_ID[self._alg], self._iv)
        return bytes(plain_text)

    def destroy(self):
        self._session.close()

    def __del__(self):
        try:
            self.destroy()
        except Exception:
            pass


class CBCCipher(EBCCipher):

    def __init__(self, session, key, iv):
        super().__init__(session, key)
        self._iv = iv
        self._alg = "sm4_cbc"