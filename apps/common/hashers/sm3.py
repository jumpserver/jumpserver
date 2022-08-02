from gmssl import sm3, func

from django.contrib.auth.hashers import PBKDF2PasswordHasher


class Hasher:
    name = 'sm3'

    def __init__(self, key):
        self.key = key

    def hexdigest(self):
        return sm3.sm3_hash(func.bytes_to_list(self.key))

    @staticmethod
    def hash(msg):
        return Hasher(msg)


class PBKDF2SM3PasswordHasher(PBKDF2PasswordHasher):
    algorithm = "pbkdf2_sm3"
    digest = Hasher.hash

