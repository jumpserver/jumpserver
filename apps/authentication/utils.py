# -*- coding: utf-8 -*-
#
import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from Crypto import Random
from django.contrib.auth import authenticate

from common.utils import get_logger

from . import errors

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


def check_user_valid(**kwargs):
    password = kwargs.pop('password', None)
    public_key = kwargs.pop('public_key', None)
    username = kwargs.pop('username', None)
    request = kwargs.get('request')

    # 获取解密密钥，对密码进行解密
    rsa_private_key = request.session.get('rsa_private_key')
    if rsa_private_key is not None:
        try:
            password = rsa_decrypt(password, rsa_private_key)
        except Exception as e:
            logger.error(e, exc_info=True)
            logger.error('Need decrypt password => {}'.format(password))
            return None, errors.reason_password_decrypt_failed

    user = authenticate(request, username=username,
                        password=password, public_key=public_key)
    if not user:
        return None, errors.reason_password_failed
    elif user.is_expired:
        return None, errors.reason_user_inactive
    elif not user.is_active:
        return None, errors.reason_user_inactive
    elif user.password_has_expired:
        return None, errors.reason_password_expired

    return user, ''
