# coding: utf-8

from jasset.models import *
from jumpserver.api import *
import uuid
import re
from ansible.playbook import PlayBook
from ansible import callbacks, utils
from jumpserver.tasks import playbook_run

from jumpserver.models import Setting
from jperm.models import PermLog


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
    log = PermLog(action=perm_info.get('action', ''))
    try:
        new_users = perm_info.get('new', {}).get('users', [])
        new_assets = perm_info.get('new', {}).get('assets', [])
        del_users = perm_info.get('del', {}).get('users', [])
        del_assets = perm_info.get('del', {}).get('assets', [])
        print new_users, new_assets
    except IndexError:
        raise ServerError("Error: function perm_user_api传入参数错误")

    try:
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
    if not results.get('failed', 1) and not results.get('unreachable', ''):
        is_success = True
    else:
        is_success = False

    log.results = results
    log.is_finish = True
    log.is_success = is_success
    log.save()
    return results


def user_group_permed(user_group):
    assets = user_group.asset.all()
    asset_groups = user_group.asset_group.all()

    for asset_group in asset_groups:
        assets.extend(asset_group.asset.all())

    return {'assets': assets, 'asset_groups': asset_groups}


def user_permed(user):
    asset_groups = []
    assets = []
    user_groups = user.group.all()
    asset_groups.extend(user.asset_group.all())
    assets.extend(user.asset.all())

    for user_group in user_groups:
        asset_groups.extend(user_group_permed(user_group).get('assets', []))
        assets.extend((user_group_permed(user_group).get('asset_groups', [])))

    return {'assets': assets, 'asset_groups': asset_groups}


def _public_perm_api(info):
    """
    公用的用户，用户组，主机，主机组编辑修改新建调用的api，用来完成授权
    info like that:
    {
      'type': 'new_user',
      'user': 'a',
      'group': ['A', 'B']
    }

    {
      'type': 'edit_user',
      'user': 'a',
      'group': {'new': ['A'], 'del': []}
    }

    {
      'type': 'del_user',
      'user': ['a', 'b']
    }

    {
      'type': 'edit_user_group',
      'group': 'A',
      'user': {'del': ['a', 'b'], 'new': ['c', 'd']}
    }

    {
      'type': 'del_user_group',
      'group': ['A']
    }

    {
      'type': 'new_asset',
      'asset': 'a',
      'group': ['A', 'B']
    }

    {
      'type': 'edit_asset',
      'asset': 'a',
      'group': {
          'del': ['A', ['B'],
          'new': ['C', ['D']]
      }
    }

    {
      'type': 'del_asset',
      'asset': ['a', 'b']
    }

    {
      'type': 'edit_asset_group',
      'group': 'A',
      'asset': {'new': ['a', 'b'], 'del': ['c', 'd']}
    }

    {
      'type': 'del_asset_group',
      'group': ['A', 'B']
    }
    """

    if info.get('type') == 'new_user':
        new_assets = []
        user = info.get('user')
        user_groups = info.get('group')
        for user_group in user_groups:
            new_assets.extend(user_group_permed(user_group).get('assets', []))

        perm_info = {
            'new': {'action': 'new user: ' + user.name, 'users': [user], 'assets': new_assets}
        }
    elif info.get('type') == 'edit_user':
        new_assets = []
        del_assets = []
        user = info.get('user')
        new_group = info.get('group').get('new')
        del_group = info.get('group').get('del')

        for user_group in new_group:
            new_assets.extend(user_group_permed(user_group).get('assets', []))

        for user_group in del_group:
            del_assets.extend((user_group_permed(user_group).get('assets', [])))

        perm_info = {
            'action': 'edit user: ' + user.name,
            'del': {'users': [user], 'assets': del_assets},
            'new': {'users': [user], 'assets': new_assets}
        }

    elif info.get('type') == 'del_user':
        user = info.get('user')
        del_assets = user_permed(user).get('assets', [])
        perm_info = {
            'action': 'del user: ' + user.name, 'del': {'users': [user], 'assets': del_assets},
        }

    elif info.get('type') == 'edit_user_group':
        user_group = info.get('group')
        new_users = info.get('user').get('new')
        del_users = info.get('user').get('del')
        assets = user_group_permed(user_group).get('assets', [])

        perm_info = {
            'action': 'edit user group: ' + user_group.name,
            'new': {'users': new_users, 'assets': assets},
            'del': {'users': del_users, 'assets': assets}
        }

    elif info.get('type') == 'del_user_group':
        user_group = info.get('group', [])
        del_users = user_group.user_set.all()
        assets = user_group_permed(user_group).get('assets', [])

        perm_info = {
            'action': "del user group: " + user_group.name, 'del': {'users': del_users, 'assets': assets}
        }
    else:
        return

    try:
        results = perm_user_api(perm_info)  # 通过API授权或回收
    except ServerError, e:
        return e
    else:
        return results










