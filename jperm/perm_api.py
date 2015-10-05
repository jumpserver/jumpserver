# coding: utf-8

from jasset.models import *
from jumpserver.api import *
import uuid
import re
from ansible.playbook import PlayBook
from ansible import callbacks, utils

from jumpserver.models import Setting


def get_object_list(model, id_list):
    object_list = []
    for object_id in id_list:
        if object_id:
            object_list.extend(model.objects.filter(id=int(object_id)))

    return object_list


def perm_user_handle(user, asset_new, asset_del, group_new, group_del):
    username = user.name
    asset_group_new = get_object_list(AssetGroup, group_new)
    asset_group_del = get_object_list(AssetGroup, group_del)
    for asset_group in asset_group_new:
        asset_new.extend([asset.ip for asset in asset_group.asset_set.all()])

    for asset_group in asset_group_del:
        asset_del.extend(asset.ip for asset in asset_group.asset_set.all())


def get_rand_file_path(base_dir=os.path.join(BASE_DIR, 'tmp')):
    filename = uuid.uuid1().hex
    return os.path.join(base_dir, filename)


def get_inventory(host_group):
    path = get_rand_file_path()
    f = open(path, 'w')
    for group, host_list in host_group.items():
        f.write('[%s]\n' % group)
        for ip in host_list:
            asset = get_object(Asset, ip=ip)
            if asset.use_default_auth:
                f.write('%s ansbile_ssh_port=%s\n' % (ip, asset.port))
            else:
                f.write('%s ansible_ssh_port=%s ansible_ssh_user=%s ansbile_ssh_pass=%s\n'
                         % (ip, asset.port, asset.username, CRYPTOR.decrypt(asset.password)))
    f.close()
    return path


def get_playbook(tempate, var):
    str_playbook = open(tempate).read()
    for k, v in var.items():
        str_playbook = re.sub(r'%s' % k, v, str_playbook)
    path = get_rand_file_path()
    f = open(path, 'w')
    f.write(str_playbook)
    return path


def perm_user_api(user, asset_new, asset_del, asset_group_new, asset_group_del):
    asset_new_ip = []
    asset_del_ip = []

    if '' in asset_group_new:
        asset_group_new.remove('')

    if '' in asset_group_del:
        asset_group_del.remove('')

    asset_new_ip.extend([asset.ip for asset in get_object_list(Asset, asset_new)])

    for asset_group_id in asset_group_new:
        asset_new_ip.extend([asset.ip for asset in get_object(AssetGroup, id=asset_group_id).asset_set.all()])

    asset_del_ip.extend([asset.ip for asset in get_object_list(Asset, asset_del)])

    for asset_group_id in asset_group_del:
        asset_del_ip.extend([asset.ip for asset in get_object(AssetGroup, id=asset_group_id).asset_set.all()])

    print asset_new_ip
    print asset_del_ip

    stats = callbacks.AggregateStats()
    playbook_cb = callbacks.PlaybookCallbacks(verbose=utils.VERBOSITY)
    runner_cb = callbacks.PlaybookRunnerCallbacks(stats, verbose=utils.VERBOSITY)

    if asset_new_ip or asset_del_ip:
        host_group = {'new': asset_new_ip, 'del': asset_del_ip}
        host_list = get_inventory(host_group)
        playbook = get_playbook(os.path.join(BASE_DIR, 'playbook', 'user_perm.yaml'),
                                {'the_new_group': 'new', 'the_del_group': 'del',
                                 'the_user': user.username, 'the_pub_key': '/tmp/id_rsa.pub'})
        settings = get_object(Setting, id=1)
        if settings:
            default_user = settings.default_user
            default_pri_key_path = settings.default_pri_key_path
        else:
            default_user = default_pri_key_path = ''
        results = PlayBook(host_list=host_list,
                           playbook=playbook,
                           forks=5,
                           remote_user=default_user,
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
