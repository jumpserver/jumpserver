# -*- coding: utf-8 -*-

import random
import os.path

from paramiko.rsakey import RSAKey
from os import chmod, makedirs
from uuid import uuid4
from django.template.loader import get_template
from django.template import Context
from tempfile import NamedTemporaryFile

from jumpserver.settings import KEY_DIR


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
    key_basename = "key-" + uuid4().hex
    key_path_dir = os.path.join(KEY_DIR, key_basename)
    makedirs(key_path_dir, 0755)

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


def get_sudo_file(sudo_chosen_aliase, sudo_chosen_obj):
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


