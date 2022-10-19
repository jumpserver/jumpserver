
from .ecc import *
from .exception import PiicoError


class BaseMixin:

    def __init__(self):
        self._driver = None
        self._session = None


class SM2Mixin(BaseMixin):
    def ecc_encrypt(self, public_key, plain_text, alg_id):

        pos = 1
        k1 = bytes([0] * 32) + bytes(public_key[pos:pos + 32])
        k1 = (c_ubyte * len(k1))(*k1)
        pos += 32
        k2 = bytes([0] * 32) + bytes(public_key[pos:pos + 32])

        pk = ECCrefPublicKey(c_uint(0x40), (c_ubyte * len(k1))(*k1), (c_ubyte * len(k2))(*k2))

        plain_text = (c_ubyte * len(plain_text))(*plain_text)
        ecc_data = new_ecc_cipher_cla(len(plain_text))()
        ret = self._driver.SDF_ExternalEncrypt_ECC(self._session, c_int(alg_id), pointer(pk), plain_text,
                                                   c_int(len(plain_text)), pointer(ecc_data))
        if ret != 0:
            raise Exception("ecc encrypt failed", ret)
        return ecc_data.encode()

    def ecc_decrypt(self, private_key, cipher_text, alg_id):

        k = bytes([0] * 32) + bytes(private_key[:32])
        vk = ECCrefPrivateKey(c_uint(0x40), (c_ubyte * len(k))(*k))

        pos = 1
        # c1
        x = bytes([0] * 32) + bytes(cipher_text[pos:pos + 32])
        pos += 32
        y = bytes([0] * 32) + bytes(cipher_text[pos:pos + 32])
        pos += 32

        # c2
        c = bytes(cipher_text[pos:-32])
        l = len(c)

        # c3
        m = bytes(cipher_text[-32:])

        ecc_data = new_ecc_cipher_cla(l)(
            (c_ubyte * 64)(*x),
            (c_ubyte * 64)(*y),
            (c_ubyte * 32)(*m),
            c_uint(l),
            (c_ubyte * l)(*c),
        )
        temp_data = (c_ubyte * l)()
        temp_data_length = c_int()
        ret = self._driver.SDF_ExternalDecrypt_ECC(self._session, c_int(alg_id), pointer(vk),
                                                   pointer(ecc_data),
                                                   temp_data, pointer(temp_data_length))
        if ret != 0:
            raise Exception("ecc decrypt failed", ret)
        return bytes(temp_data[:temp_data_length.value])


class SM3Mixin(BaseMixin):
    def hash_init(self, alg_id):
        ret = self._driver.SDF_HashInit(self._session, c_int(alg_id), None, None, c_int(0))
        if ret != 0:
            raise PiicoError("hash init failed,alg id is {}".format(alg_id), ret)

    def hash_update(self, data):
        data = (c_ubyte * len(data))(*data)
        ret = self._driver.SDF_HashUpdate(self._session, data, c_int(len(data)))
        if ret != 0:
            raise PiicoError("hash update failed", ret)

    def hash_final(self):
        result_data = (c_ubyte * 32)()
        result_length = c_int()
        ret = self._driver.SDF_HashFinal(self._session, result_data, pointer(result_length))
        if ret != 0:
            raise PiicoError("hash final failed", ret)
        return bytes(result_data[:result_length.value])


class SM4Mixin(BaseMixin):

    def import_key(self, key_val):
        # to c lang
        key_val = (c_ubyte * len(key_val))(*key_val)

        key = c_void_p()
        ret = self._driver.SDF_ImportKey(self._session, key_val, c_int(len(key_val)), pointer(key))
        if ret != 0:
            raise PiicoError("import key failed", ret)
        return key

    def destroy_cipher_key(self, key):
        ret = self._driver.SDF_DestroyKey(self._session, key)
        if ret != 0:
            raise Exception("destroy key failed")

    def encrypt(self, plain_text, key, alg, iv=None):
        return self.__do_cipher_action(plain_text, key, alg, iv, True)

    def decrypt(self, cipher_text, key, alg, iv=None):
        return self.__do_cipher_action(cipher_text, key, alg, iv, False)

    def __do_cipher_action(self, text, key, alg, iv=None, encrypt=True):
        text = (c_ubyte * len(text))(*text)
        if iv is not None:
            iv = (c_ubyte * len(iv))(*iv)

        temp_data = (c_ubyte * len(text))()
        temp_data_length = c_int()
        if encrypt:
            ret = self._driver.SDF_Encrypt(self._session, key, c_int(alg), iv, text, c_int(len(text)), temp_data,
                                           pointer(temp_data_length))
            if ret != 0:
                raise PiicoError("encrypt failed", ret)
        else:
            ret = self._driver.SDF_Decrypt(self._session, key, c_int(alg), iv, text, c_int(len(text)), temp_data,
                                           pointer(temp_data_length))
            if ret != 0:
                raise PiicoError("decrypt failed", ret)
        return temp_data[:temp_data_length.value]
