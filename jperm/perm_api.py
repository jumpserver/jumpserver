# coding: utf-8

from jasset.models import *
from jumpserver.api import *
import uuid
import re
from ansible.playbook import PlayBook
from ansible import callbacks, utils
from jumpserver.tasks import playbook_run, add

from jumpserver.models import Setting


def get_object_list(model, id_list):
    """根据id列表获取对象列表"""
    object_list = []
    for object_id in id_list:
        if object_id:
            object_list.extend(model.objects.filter(id=int(object_id)))

    return object_list


def get_rand_file_path(base_dir=os.path.join(BASE_DIR, 'tmp')):
    """获取随机文件路径"""
    filename = uuid.uuid1().hex
    return os.path.join(base_dir, filename)


def get_inventory(host_group):
    """生成资产表库存清单"""
    path = get_rand_file_path()
    f = open(path, 'w')
    for group, host_list in host_group.items():
        f.write('[%s]\n' % group)
        for ip in host_list:
            asset = get_object(Asset, ip=ip)
            if asset.use_default:
                f.write('%s\n' % ip)
            else:
                f.write('%s ansible_ssh_port=%s ansible_ssh_user=%s ansible_ssh_pass=%s\n' %
                        (ip, asset.port, asset.username, CRYPTOR.decrypt(asset.password)))
    f.close()
    return path


def get_playbook(template, var):
    """根据playbook模板，生成playbook"""
    str_playbook = open(template).read()
    for k, v in var.items():
        str_playbook = re.sub(r'%s' % k, v, str_playbook)  # 正则来替换传入的字符
    path = get_rand_file_path()
    f = open(path, 'w')
    f.write(str_playbook)
    return path


def perm_user_api(perm_info):
    """
    用户授权api，通过调用ansible API完成用户新建等,传入参数必须如下,列表中可以是对象，也可以是用户名和ip
    perm_info = {'del': {'users': [],
                         'assets': [],
                        },
                 'new': {'users': [],
                         'assets': []}}
    """
    try:
        new_users = perm_info['new']['users']
        new_assets = perm_info['new']['assets']
        del_users = perm_info['del']['users']
        del_assets = perm_info['del']['assets']

        print new_users, new_assets
    except IndexError:
        raise ServerError("Error: function perm_user_api传入参数错误")

    # 检查传入的是字符串还是对象
    check_users = new_users + del_users
    try:
        if isinstance(check_users[0], str):
            var_type = 'str'
        else:
            var_type = 'obj'

    except IndexError:
        raise ServerError("Error: function perm_user_api传入参数错误")

    try:
        if var_type == 'str':
            new_ip = new_assets
            del_ip = del_assets
            new_username = new_users
            del_username = del_users
        else:
            new_ip = [asset.ip for asset in new_assets if isinstance(asset, Asset)]
            del_ip = [asset.ip for asset in del_assets if isinstance(asset, Asset)]
            new_username = [user.username for user in new_users if isinstance(user, User)]
            del_username = [user.username for user in del_users if isinstance(user, User)]
    except IndexError:
        raise ServerError("Error: function perm_user_api传入参数类型错误")

    host_group = {'new': new_ip, 'del': del_ip}
    inventory = get_inventory(host_group)

    the_new_users = ','.join(new_username)
    the_del_users = ','.join(del_username)

    playbook = get_playbook(os.path.join(BASE_DIR, 'playbook', 'user_perm.yaml'),
                            {'the_new_group': 'new', 'the_del_group': 'del',
                             'the_new_users': the_new_users, 'the_del_users': the_del_users,
                             'the_pub_key': '/tmp/id_rsa.pub'})

    print playbook, inventory

    settings = get_object(Setting, name='default')
    results = playbook_run(inventory, playbook, settings)
    return results


def get_user_assets(user):
    if isinstance(user, int):
        user = get_object(User, id=user)
    elif isinstance(user, str):
        user = get_object(User, username=user)
    elif isinstance(user, User):
        user = user
    else:
        user = None


def refresh_group_api(user_group=None, asset_group=None):
    """用户组添加删除用户，主机组添加删除主机触发"""
    pass

