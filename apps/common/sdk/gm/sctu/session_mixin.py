from ctypes import *

from common.sdk.gm.base.exception import GMDeviceError
from common.sdk.gm.base.session_mixin import BaseMixin


SGD_SM4_ECB = 0x00002001
SGD_SM4_CBC = 0x00002002

PADDING_PKCS7 = "pkcs7"
PADDING_ZERO = "zero"
PADDING_NONE = "none"


def as_uchar_array(data: bytes):
    if data is None:
        return None
    if not isinstance(data, (bytes, bytearray)):
        raise TypeError("data must be bytes or bytearray")
    return (c_ubyte * len(data)).from_buffer_copy(bytes(data))


def zero_pad(data: bytes, block_size: int = 16) -> bytes:
    pad_len = (-len(data)) % block_size
    if pad_len == 0:
        return data
    return data + b"\x00" * pad_len


def zero_unpad(data: bytes) -> bytes:
    return data.rstrip(b"\x00")


def pkcs7_pad(data: bytes, block_size: int = 16) -> bytes:
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len]) * pad_len


def pkcs7_unpad(data: bytes, block_size: int = 16) -> bytes:
    if not data:
        raise ValueError("empty plaintext after decrypt")

    pad_len = data[-1]
    if pad_len < 1 or pad_len > block_size:
        raise ValueError("invalid pkcs7 padding")

    if data[-pad_len:] != bytes([pad_len]) * pad_len:
        raise ValueError("bad pkcs7 padding")

    return data[:-pad_len]


class SM4Mixin(BaseMixin):
    """
    SM4 外部明文 key 加解密。

    注意：
    1. 按当前 SDK 实测，key 允许 16 字节的整数倍。
    2. CBC 模式 iv 必须是 16 字节。
    3. SDF 接口要求输入数据长度必须是 16 的整数倍。
    4. 默认使用 zero padding，解决你现在解密后结尾多 0 的问题。
    """

    def import_key(self, key_val):
        pass

    def destroy_cipher_key(self, key):
        pass

    def encrypt(
        self,
        plain_text: bytes,
        key: bytes,
        alg: int,
        iv: bytes = None,
        padding: str = PADDING_ZERO,
    ) -> bytes:
        return self.__do_cipher_action(
            plain_text,
            key,
            alg,
            iv,
            encrypt=True,
            padding=padding,
        )

    def decrypt(
        self,
        cipher_text: bytes,
        key: bytes,
        alg: int,
        iv: bytes = None,
        padding: str = PADDING_ZERO,
    ) -> bytes:
        return self.__do_cipher_action(
            cipher_text,
            key,
            alg,
            iv,
            encrypt=False,
            padding=padding,
        )

    def __do_cipher_action(
        self,
        text: bytes,
        key: bytes,
        alg: int,
        iv: bytes = None,
        encrypt: bool = True,
        padding: str = PADDING_ZERO,
    ) -> bytes:
        if not isinstance(text, (bytes, bytearray)):
            raise TypeError("text must be bytes or bytearray")

        if not isinstance(key, (bytes, bytearray)):
            raise TypeError("key must be bytes or bytearray")

        text = bytes(text)
        key = bytes(key)

        if len(key) == 0 or len(key) % 16 != 0:
            raise ValueError("SM4 external key length must be multiple of 16 bytes")

        if alg == SGD_SM4_CBC:
            if iv is None:
                raise ValueError("SM4 CBC mode requires 16 bytes iv")
            if not isinstance(iv, (bytes, bytearray)):
                raise TypeError("iv must be bytes or bytearray")
            iv = bytes(iv)
            if len(iv) != 16:
                raise ValueError("SM4 CBC iv must be 16 bytes")
            iv_arr = as_uchar_array(iv)

        elif alg == SGD_SM4_ECB:
            iv_arr = None

        else:
            raise ValueError(f"unsupported SM4 alg: 0x{alg:08x}")

        if encrypt:
            if padding == PADDING_PKCS7:
                text = pkcs7_pad(text, 16)
            elif padding == PADDING_ZERO:
                text = zero_pad(text, 16)
            elif padding == PADDING_NONE:
                if len(text) == 0 or len(text) % 16 != 0:
                    raise ValueError("plain text length must be multiple of 16 bytes when padding is none")
            else:
                raise ValueError(f"unsupported padding: {padding}")
        else:
            if len(text) == 0 or len(text) % 16 != 0:
                raise ValueError("cipher text length must be multiple of 16 bytes")

        text_arr = as_uchar_array(text)
        key_arr = as_uchar_array(key)

        temp_data = (c_ubyte * (len(text) + 16))()
        temp_data_length = c_uint32(len(temp_data))

        if encrypt:
            ret = self._driver.HS_SDF_Encrypt(
                self._session,
                key_arr,
                c_uint32(len(key)),
                c_uint32(0),
                c_uint32(alg),
                iv_arr,
                text_arr,
                c_uint32(len(text)),
                temp_data,
                byref(temp_data_length),
            )

            if ret != 0:
                raise GMDeviceError("encrypt failed", ret)

            return bytes(temp_data[:temp_data_length.value])

        ret = self._driver.HS_SDF_Decrypt(
            self._session,
            key_arr,
            c_uint32(len(key)),
            c_uint32(0),
            c_uint32(alg),
            iv_arr,
            text_arr,
            c_uint32(len(text)),
            temp_data,
            byref(temp_data_length),
        )

        if ret != 0:
            raise GMDeviceError("decrypt failed", ret)

        plain = bytes(temp_data[:temp_data_length.value])

        if padding == PADDING_PKCS7:
            return pkcs7_unpad(plain, 16)

        if padding == PADDING_ZERO:
            return zero_unpad(plain)

        if padding == PADDING_NONE:
            return plain

        raise ValueError(f"unsupported padding: {padding}")