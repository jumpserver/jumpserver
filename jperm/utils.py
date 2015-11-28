# -*- coding: utf-8 -*-

import random
import os.path
import shutil
from paramiko import SSHException
from paramiko.rsakey import RSAKey
from jumpserver.api import mkdir
from uuid import uuid4
from jumpserver.api import CRYPTOR
from os import makedirs

from django.template.loader import get_template
from django.template import Context
from tempfile import NamedTemporaryFile


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
    mkdir(key_path_dir, mode=0755)
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
            except SSHException:
                shutil.rmtree(key_path_dir, ignore_errors=True)
                raise SSHException
    os.chmod(private_key, 0644)

    with open(public_key, 'w') as content_file:
        for data in [key.get_name(),
                     " ",
                     key.get_base64(),
                     " %s@%s" % ("jumpserver", os.uname()[1])]:
            content_file.write(data)
    return key_path_dir


def gen_sudo(role_custom, role_name, role_chosen):
    """
    生成sudo file, 仅测试了cenos7
    role_custom: 自定义支持的sudo 命令　格式: 'CMD1, CMD2, CMD3, ...'
    role_name: role name
    role_chosen: 选择那些sudo的命令别名：
    　　　　NETWORKING, SOFTWARE, SERVICES, STORAGE,
    　　　　DELEGATING, PROCESSES, LOCATE, DRIVERS
    :return:
    """
    sudo_file_basename = os.path.join(os.path.dirname(KEY_DIR), 'role_sudo_file')
    makedirs(sudo_file_basename)
    sudo_file_path = os.path.join(sudo_file_basename, role_name)

    t = get_template('role_sudo.j2')
    content = t.render(Context({"role_custom": role_custom,
                      "role_name": role_name,
                      "role_chosen": role_chosen,
                      }))
    with open(sudo_file_path, 'w') as f:
        f.write(content)
    return sudo_file_path


def get_add_sudo_script(sudo_chosen_aliase, sudo_chosen_obj):
    """
    get the sudo file
    :param kwargs:
    :return:
    """
    sudo_j2 = get_template('jperm/role_sudo.j2')
    sudo_content = sudo_j2.render(Context({"sudo_chosen_aliase": sudo_chosen_aliase,
                                           "sudo_chosen_obj": sudo_chosen_obj}))
    sudo_file = NamedTemporaryFile(delete=False)
    sudo_file.write(sudo_content)
    sudo_file.close()

    return sudo_file.name



if __name__ == "__main__":
    print gen_keys()


