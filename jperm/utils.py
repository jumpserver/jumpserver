# -*- coding: utf-8 -*-

import os.path
import shutil
from paramiko import SSHException
from paramiko.rsakey import RSAKey
from jumpserver.api import mkdir
from uuid import uuid4
from jumpserver.api import CRYPTOR

from jumpserver.api import logger


from jumpserver.settings import KEY_DIR


def get_rand_pass():
    """
    get a reandom password.
    """
    CRYPTOR.gen_rand_pass(20)


def updates_dict(*args):
    """
    surport update multi dict
    """
    result = {}
    for d in args:
        result.update(d)
    return result


def gen_keys(key="", key_path_dir=""):
    """
    在KEY_DIR下创建一个 uuid命名的目录，
    并且在该目录下 生产一对秘钥
    :return: 返回目录名(uuid)
    """
    key_basename = "key-" + uuid4().hex
    if not key_path_dir:
        key_path_dir = os.path.join(KEY_DIR, 'role_key', key_basename)
    private_key = os.path.join(key_path_dir, 'id_rsa')
    public_key = os.path.join(key_path_dir, 'id_rsa.pub')
    mkdir(key_path_dir, mode=755)
    if not key:
        key = RSAKey.generate(2048)
        key.write_private_key_file(private_key)
    else:
        key_file = os.path.join(key_path_dir, 'id_rsa')
        with open(key_file, 'w') as f:
            f.write(key)
            f.close()
        with open(key_file) as f:
            try:
                key = RSAKey.from_private_key(f)
            except SSHException, e:
                shutil.rmtree(key_path_dir, ignore_errors=True)
                raise SSHException(e)
    os.chmod(private_key, 0644)

    with open(public_key, 'w') as content_file:
        for data in [key.get_name(),
                     " ",
                     key.get_base64(),
                     " %s@%s" % ("jumpserver", os.uname()[1])]:
            content_file.write(data)
    return key_path_dir


def trans_all(str):
    if str.strip().lower() == "all":
        return str.upper()
    else:
        return str

if __name__ == "__main__":
    print gen_keys()


