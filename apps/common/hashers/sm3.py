from gmssl import sm3, func

from django.contrib.auth.hashers import PBKDF2PasswordHasher


class Hasher:
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
    def hash(msg=b''):
        return Hasher(msg)

    def update(self, data):
        self.__data += data

    def copy(self):
        return Hasher(self.__data)


class PBKDF2SM3PasswordHasher(PBKDF2PasswordHasher):
    algorithm = "pbkdf2_sm3"
    digest = Hasher.hash

