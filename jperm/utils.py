# -*- coding: utf-8 -*-

import random
import os.path

from paramiko.rsakey import RSAKey
from os import chmod, mkdir
from uuid import uuid4

PERM_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_DIR = os.path.join(PERM_DIR, 'role_keys')


def get_rand_pass():
    """
    get a reandom password.
    """
    lower = [chr(i) for i in range(97,123)]
    upper = [chr(i).upper() for i in range(97,123)]
    digit = [str(i) for i in range(10)]
    password_pool = []
    password_pool.extend(lower)
    password_pool.extend(upper)
    password_pool.extend(digit)
    pass_list = [random.choice(password_pool) for i in range(1,14)]
    pass_list.insert(random.choice(range(1,14)), '@')
    pass_list.insert(random.choice(range(1,14)), random.choice(digit))
    password = ''.join(pass_list)
    return password


def updates_dict(*args):
    """
    surport update multi dict
    """
    result = {}
    for d in args:
        result.update(d)
    return result


def gen_keys():
    """
    在KEY_DIR下创建一个 uuid命名的目录，
    并且在该目录下 生产一对秘钥
    :return: 返回目录名(uuid)
    """
    key_basename = "keys-" + uuid4().hex
    key_path_dir = os.path.join(KEY_DIR, key_basename)
    mkdir(key_path_dir, 0700)

    key = RSAKey.generate(2048)
    private_key = os.path.join(key_path_dir, 'id_rsa')
    public_key = os.path.join(key_path_dir, 'id_rsa.pub')
    key.write_private_key_file(private_key)

    with open(public_key, 'w') as content_file:
        for data in [key.get_name(),
                     " ",
                     key.get_base64(),
                     " %s@%s" % ("jumpserver", os.uname()[1])]:
            content_file.write(data)
    return key_path_dir




if __name__ == "__main__":
    print gen_keys()


