import base64


class BaseCrypto:
    def encrypt(self, text):
        return base64.urlsafe_b64encode(
            self._encrypt(bytes(text, encoding='utf8'))
        ).decode('utf8')

    def encrypt_bin(self, data: bytes) -> bytes:
        return self._encrypt(data)

    def _encrypt(self, data: bytes) -> bytes:
        raise NotImplementedError

    def decrypt_bin(self, data: bytes) -> bytes:
        return self._decrypt(data)

    def decrypt(self, text):
        return self._decrypt(
            base64.urlsafe_b64decode(bytes(text, encoding='utf8'))
        ).decode('utf8')

    def _decrypt(self, data: bytes) -> bytes:
        raise NotImplementedError


class BaseCryptoSuite:
    def encrypt(self, text):
        raise NotImplementedError

    def decrypt(self, cipher_text):
        raise NotImplementedError

    def gen_key_pair(self):
        raise NotImplementedError

    def encrypt_with_key_pair(self, text, public_key):
        raise NotImplementedError

    def decrypt_with_key_pair(self, cipher_text, private_key):
        raise NotImplementedError

    def hash(self):
        raise NotImplementedError