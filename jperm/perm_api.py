# coding: utf-8

from django.db.models.query import QuerySet
from jumpserver.api import *
import uuid
import re

from jumpserver.models import Setting
from jperm.models import PermRole, PermPush, PermRule


def get_group_user_perm(ob):
    """
    ob为用户或用户组
    获取用户、用户组授权的资产、资产组
    return:
    {’asset_group': {
            asset_group1: {'asset': [], 'role': [role1, role2], 'rule': [rule1, rule2]},
            asset_group2: {'asset: [], 'role': [role1, role2], 'rule': [rule1, rule2]},
            }
    'asset':{
            asset1: {'role': [role1, role2], 'rule': [rule1, rule2]},
            asset2: {'role': [role1, role2], 'rule': [rule1, rule2]},
            }
        ]},
    'rule':[rule1, rule2,]
    'role': {role1: {'asset': []}, 'asset_group': []}, role2: {}},
    }
    """
    perm = {}
    if isinstance(ob, User):
        rule_all = set(PermRule.objects.filter(user=ob))
        for user_group in ob.group.all():
            rule_all = rule_all.union(set(PermRule.objects.filter(user_group=user_group)))

    elif isinstance(ob, UserGroup):
        rule_all = PermRule.objects.filter(user_group=ob)
    else:
        rule_all = []

    perm['rule'] = rule_all
    perm_asset_group = perm['asset_group'] = {}
    perm_asset = perm['asset'] = {}
    perm_role = perm['role'] = {}
    for rule in rule_all:
        asset_groups = rule.asset_group.all()
        assets = rule.asset.all()
        perm_roles = rule.role.all()
        group_assets = []
        for asset_group in asset_groups:
            group_assets.extend(asset_group.asset_set.all())
        # 获取一个规则授权的角色和对应主机
        for role in perm_roles:
            if perm_role.get(role):
                perm_role[role]['asset'] = perm_role[role].get('asset', set()).union(set(assets).union(set(group_assets)))
                perm_role[role]['asset_group'] = perm_role[role].get('asset_group', set()).union(set(asset_groups))
            else:
                perm_role[role] = {'asset': set(assets).union(set(group_assets)), 'asset_group': set(asset_groups)}

        # 获取一个规则用户授权的资产
        for asset in assets:
            if perm_asset.get(asset):
                perm_asset[asset].get('role', set()).update(set(rule.role.all()))
                perm_asset[asset].get('rule', set()).add(rule)
            else:
                perm_asset[asset] = {'role': set(rule.role.all()), 'rule': set([rule])}

        # 获取一个规则用户授权的资产组
        for asset_group in asset_groups:
            asset_group_assets = asset_group.asset_set.all()
            if perm_asset_group.get(asset_group):
                perm_asset_group[asset_group].get('role', set()).update(set(rule.role.all()))
                perm_asset_group[asset_group].get('rule', set()).add(rule)
            else:
                perm_asset_group[asset_group] = {'role': set(rule.role.all()), 'rule': set([rule]),
                                                 'asset': asset_group_assets}

            # 将资产组中的资产添加到资产授权中
            for asset in asset_group_assets:
                if perm_asset.get(asset):
                    perm_asset[asset].get('role', set()).update(perm_asset_group[asset_group].get('role', set()))
                    perm_asset[asset].get('rule', set()).update(perm_asset_group[asset_group].get('rule', set()))
                else:
                    perm_asset[asset] = {'role': perm_asset_group[asset_group].get('role', set()),
                                         'rule': perm_asset_group[asset_group].get('rule', set())}
    return perm


def get_group_asset_perm(ob):
    """
    ob为资产或资产组
    获取资产，资产组授权的用户，用户组
    return:
    {’user_group': {
            user_group1: {'user': [], 'role': [role1, role2], 'rule': [rule1, rule2]},
            user_group2: {'user: [], 'role': [role1, role2], 'rule': [rule1, rule2]},
            }
    'user':{
            user1: {'role': [role1, role2], 'rule': [rule1, rule2]},
            user2: {'role': [role1, role2], 'rule': [rule1, rule2]},
            }
        ]},
    'rule':[rule1, rule2,],
    }
    """
    perm = {}
    if isinstance(ob, Asset):
        rule_all = PermRule.objects.filter(asset=ob)
    elif isinstance(ob, AssetGroup):
        rule_all = PermRule.objects.filter(asset_group=ob)
    else:
        rule_all = []

    perm['rule'] = rule_all
    perm_user_group = perm['user_group'] = {}
    perm_user = perm['user'] = {}
    for rule in rule_all:
        user_groups = rule.user_group.all()
        users = rule.user.all()
        # 获取一个规则资产的用户
        for user in users:
            if perm_user.get(user):
                perm_user[user].get('role', set()).update(set(rule.role.all()))
                perm_user[user].get('rule', set()).add(rule)
            else:
                perm_user[user] = {'role': set(rule.role.all()), 'rule': set([rule])}

        # 获取一个规则资产授权的用户组
        for user_group in user_groups:
            user_group_users = user_group.user_set.all()
            if perm_user_group.get(user_group):
                perm_user_group[user_group].get('role', set()).update(set(rule.role.all()))
                perm_user_group[user_group].get('rule', set()).add(rule)
            else:
                perm_user_group[user_group] = {'role': set(rule.role.all()), 'rule': set([rule]),
                                               'user': user_group_users}

            # 将用户组中的资产添加到用户授权中
            for user in user_group_users:
                if perm_user.get(user):
                    perm_user[user].get('role', set()).update(perm_user_group[user_group].get('role', set()))
                    perm_user[user].get('rule', set()).update(perm_user_group[user_group].get('rule', set()))
                else:
                    perm_user[user] = {'role': perm_user_group[user_group].get('role', set()),
                                       'rule': perm_user_group[user_group].get('rule', set())}
    return perm


def user_have_perm(user, asset):
    user_perm_all = get_group_user_perm(user)
    user_assets = user_perm_all.get('asset').keys()
    if asset in user_assets:
        return user_perm_all.get('asset').get(asset).get('role')
    else:
        return []


def gen_resource(ob, perm=None):
    """
    ob为用户或资产列表或资产queryset, 如果同时输入用户和{'role': role1, 'asset': []}，则获取用户在这些资产上的信息
    生成MyInventory需要的 resource文件
    """
    res = []
    if isinstance(ob, dict):
        role = ob.get('role')
        asset_r = ob.get('asset')
        user = ob.get('user')
        if not perm:
            perm = get_group_user_perm(user)

        if role:
            roles = perm.get('role', {}).keys()  # 获取用户所有授权角色
            if role not in roles:
                return {}

            role_assets_all = perm.get('role').get(role).get('asset')  # 获取用户该角色所有授权主机
            assets = set(role_assets_all) & set(asset_r)  # 获取用户提交中合法的主机

            for asset in assets:
                asset_info = get_asset_info(asset)
                role_key = get_role_key(user, role)
                info = {'hostname': asset.hostname,
                        'ip': asset.ip,
                        'port': asset_info.get('port', 22),
                        'ansible_ssh_private_key_file': role_key,
                        'username': role.name,
                        # 'password': CRYPTOR.decrypt(role.password)
                       }

                if os.path.isfile(role_key):
                    info['ssh_key'] = role_key

                res.append(info)
        else:
            for asset, asset_info in perm.get('asset').items():
                if asset not in asset_r:
                    continue
                asset_info = get_asset_info(asset)
                try:
                    role = sorted(list(perm.get('asset').get(asset).get('role')))[0]
                except IndexError:
                    continue

                role_key = get_role_key(user, role)
                info = {'hostname': asset.hostname,
                        'ip': asset.ip,
                        'port': asset_info.get('port', 22),
                        'username': role.name,
                        'password': CRYPTOR.decrypt(role.password),
                        }
                if os.path.isfile(role_key):
                    info['ssh_key'] = role_key

                res.append(info)

    elif isinstance(ob, User):
        if not perm:
            perm = get_group_user_perm(ob)

        for asset, asset_info in perm.get('asset').items():
            asset_info = get_asset_info(asset)
            info = {'hostname': asset.hostname, 'ip': asset.ip, 'port': asset_info.get('port', 22)}
            try:
                role = sorted(list(perm.get('asset').get(asset).get('role')))[0]
            except IndexError:
                continue
            info['username'] = role.name
            info['password'] = CRYPTOR.decrypt(role.password)

            role_key = get_role_key(ob, role)
            if os.path.isfile(role_key):
                    info['ssh_key'] = role_key
            res.append(info)

    elif isinstance(ob, (list, QuerySet)):
        for asset in ob:
            info = get_asset_info(asset)
            res.append(info)
    logger.debug('生成res: %s' % res)
    return res


def get_object_list(model, id_list):
    """根据id列表获取对象列表"""
    object_list = []
    for object_id in id_list:
        if object_id:
            object_list.extend(model.objects.filter(id=int(object_id)))

    return object_list


def get_role_info(role_id, type="all"):
    """
    获取role对应的一些信息
    :return: 返回值 均为对象列表
    """
    # 获取role对应的授权规则
    role_obj = PermRole.objects.get(id=role_id)
    rule_push_obj = role_obj.perm_rule.all()
    # 获取role 对应的用户 和 用户组
    # 获取role 对应的主机 和主机组
    users_obj = []
    assets_obj = []
    user_groups_obj = []
    asset_groups_obj = []
    for push in rule_push_obj:
        for user in push.user.all():
            users_obj.append(user)
        for asset in push.asset.all():
            assets_obj.append(asset)
        for user_group in push.user_group.all():
            user_groups_obj.append(user_group)
        for asset_group in push.asset_group.all():
            asset_groups_obj.append(asset_group)

    if type == "all":
        return {"rules": set(rule_push_obj),
                "users": set(users_obj),
                "user_groups": set(user_groups_obj),
                "assets": set(assets_obj),
                "asset_groups": set(asset_groups_obj),
                }

    elif type == "rule":
        return set(rule_push_obj)
    elif type == "user":
        return set(users_obj)
    elif type == "user_group":
        return set(user_groups_obj)
    elif type == "asset":
        return set(assets_obj)
    elif type == "asset_group":
        return set(asset_groups_obj)
    else:
        return u"不支持的查询"


def get_role_push_host(role):
    """
    asset_pushed: {'success': push.success, 'key': push.is_public_key, 'password': push.is_password,
                   'result': push.result}
    asset_no_push: set(asset1, asset2)
    """
    # 计算该role 所有push记录 总共推送的主机
    pushs = PermPush.objects.filter(role=role)
    asset_all = Asset.objects.all()
    asset_pushed = {}
    for push in pushs:
        asset_pushed[push.asset] = {'success': push.success, 'key': push.is_public_key, 'password': push.is_password,
                                    'result': push.result}
    asset_no_push = set(asset_all) - set(asset_pushed.keys())
    return asset_pushed, asset_no_push


if __name__ == "__main__":
    print get_role_info(1)

