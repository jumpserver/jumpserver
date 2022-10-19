cipher_alg_id = {
    "sm4_ebc": 0x00000401,
    "sm4_cbc": 0x00000402,
}


class ECCCipher:
    def __init__(self, session, public_key, private_key):
        self._session = session
        self.public_key = public_key
        self.private_key = private_key

    def encrypt(self, plain_text):
        return self._session.ecc_encrypt(self.public_key, plain_text, 0x00020800)

    def decrypt(self, cipher_text):
        return self._session.ecc_decrypt(self.private_key, cipher_text, 0x00020800)


class EBCCipher:

    def __init__(self, session, key_val):
        self._session = session
        self._key = self.__get_key(key_val)
        self._alg = "sm4_ebc"
        self._iv = None

    def __get_key(self, key_val):
        key_val = self.__padding(key_val)
        return self._session.import_key(key_val)

    @staticmethod
    def __padding(val):
        # padding
        val = bytes(val)
        while len(val) == 0 or len(val) % 16 != 0:
            val += b'\0'
        return val

    def encrypt(self, plain_text):
        plain_text = self.__padding(plain_text)
        cipher_text = self._session.encrypt(plain_text, self._key, cipher_alg_id[self._alg], self._iv)
        return bytes(cipher_text)

    def decrypt(self, cipher_text):
        plain_text = self._session.decrypt(cipher_text, self._key, cipher_alg_id[self._alg], self._iv)
        return bytes(plain_text)

    def destroy(self):
        self._session.destroy_cipher_key(self._key)
        self._session.close()


class CBCCipher(EBCCipher):

    def __init__(self, session, key, iv):
        super().__init__(session, key)
        self._iv = iv
        self._alg = "sm4_cbc"
