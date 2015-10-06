# coding: utf-8

from jasset.models import *
from jumpserver.api import *
import uuid
import re
from ansible.playbook import PlayBook
from ansible import callbacks, utils

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


def playbook_run(inventory, playbook, default_user=None, default_port=None, default_pri_key_path=None):
    stats = callbacks.AggregateStats()
    playbook_cb = callbacks.PlaybookCallbacks(verbose=utils.VERBOSITY)
    runner_cb = callbacks.PlaybookRunnerCallbacks(stats, verbose=utils.VERBOSITY)
    # run the playbook
    results = PlayBook(host_list=inventory,
                       playbook=playbook,
                       forks=5,
                       remote_user=default_user,
                       remote_port=default_port,
                       private_key_file=default_pri_key_path,
                       callbacks=playbook_cb,
                       runner_callbacks=runner_cb,
                       stats=stats,
                       become=True,
                       become_user='root').run()

    for hostname, result in results.items():
        if result.get('failures', 2):
            print "%s >>> Failed" % hostname
        else:
            print "%s >>> Success" % hostname
    return results


def perm_user_api(asset_new, asset_del, asset_group_new, asset_group_del, user=None, user_group=None):
    """用户授权api，通过调用ansible API完成用户新建等"""
    asset_new_ip = []  # 新授权的ip列表
    asset_del_ip = []  # 回收授权的ip列表

    if '' in asset_group_new:
        asset_group_new.remove('')

    if '' in asset_group_del:
        asset_group_del.remove('')

    asset_new_ip.extend([asset.ip for asset in get_object_list(Asset, asset_new)])  # 查库，获取新授权ip
    for asset_group_id in asset_group_new:
        asset_new_ip.extend([asset.ip for asset in get_object(AssetGroup, id=asset_group_id).asset_set.all()])  # 同理
    asset_del_ip.extend([asset.ip for asset in get_object_list(Asset, asset_del)])  # 查库，获取回收授权的ip
    for asset_group_id in asset_group_del:
        asset_del_ip.extend([asset.ip for asset in get_object(AssetGroup, id=asset_group_id).asset_set.all()])  # 同理

    print asset_new_ip
    print asset_del_ip

    if asset_new_ip or asset_del_ip:
        host_group = {'new': asset_new_ip, 'del': asset_del_ip}
        inventory = get_inventory(host_group)
        if user:
            the_items = user.username,
        elif user_group:
            users = user_group.user_set.all()
            the_items = ','.join([user.username for user in users])
        else:
            return HttpResponse('Argument error.')

        playbook = get_playbook(os.path.join(BASE_DIR, 'playbook', 'user_perm.yaml'),
                                {'the_new_group': 'new', 'the_del_group': 'del',
                                 'the_items': the_items, 'the_pub_key': '/tmp/id_rsa.pub'})

        settings = get_object(Setting, id=1)
        if settings:
            default_user = settings.default_user
            default_port = settings.default_port
            default_pri_key_path = settings.default_pri_key_path
        else:
            default_user = default_port = default_pri_key_path = ''

        results = playbook_run(inventory, playbook, default_user, default_port, default_pri_key_path)
        return results


def refresh_group_api(user_group=None, asset_group=None):
    """用户组添加删除用户，主机组添加删除主机触发"""
    pass

