# -*- coding: utf-8 -*-
#
import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from Crypto import Random

from common.utils import get_logger

logger = get_logger(__file__)


def gen_key_pair():
    """ 生成加密key
    用于登录页面提交用户名/密码时，对密码进行加密（前端）/解密（后端）
    """
    random_generator = Random.new().read
    rsa = RSA.generate(1024, random_generator)
    rsa_private_key = rsa.exportKey().decode()
    rsa_public_key = rsa.publickey().exportKey().decode()
    return rsa_private_key, rsa_public_key


def rsa_encrypt(message, rsa_public_key):
    """ 加密登录密码 """
    key = RSA.importKey(rsa_public_key)
    cipher = PKCS1_v1_5.new(key)
    cipher_text = base64.b64encode(cipher.encrypt(message.encode())).decode()
    return cipher_text


def rsa_decrypt(cipher_text, rsa_private_key=None):
    """ 解密登录密码 """
    if rsa_private_key is None:
        # rsa_private_key 为 None，可以能是API请求认证，不需要解密
        return cipher_text
    key = RSA.importKey(rsa_private_key)
    cipher = PKCS1_v1_5.new(key)
    message = cipher.decrypt(base64.b64decode(cipher_text.encode()), 'error').decode()
    return message
