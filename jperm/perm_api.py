# coding: utf-8

from django.db.models.query import QuerySet
from jumpserver.api import *
import uuid
import re

from jumpserver.models import Setting
from jperm.models import PermRole
from jperm.models import PermRule


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
    }
    """
    perm = {}
    if isinstance(ob, User):
        rule_all = PermRule.objects.filter(user=ob)
    elif isinstance(ob, UserGroup):
        rule_all = PermRule.objects.filter(user_group=ob)
    else:
        rule_all = []

    perm['rule'] = rule_all
    perm_asset_group = perm['asset_group'] = {}
    perm_asset = perm['asset'] = {}
    for rule in rule_all:
        asset_groups = rule.asset_group.all()
        assets = rule.asset.all()

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
    'rule':[rule1, rule2,]
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


def gen_resource(ob):
    """
    ob为用户或资产列表或资产queryset
    生成MyInventory需要的 resource文件
    """
    res = []
    if isinstance(ob, User):
        perm = get_group_user_perm(ob)
        for asset, asset_info in perm.get('asset').items():
            info = {'hostname': asset.hostname, 'ip': asset.ip, 'port': asset.port}
            try:
                role = sorted(list(asset_info.get('role')))[0]
            except IndexError:
                continue
            info['username'] = role.name
            info['password'] = role.password
            info['key_path'] = role.key_path
            res.append(info)
    elif isinstance(ob, (list, QuerySet)):
        default = get_object(Setting, name='default')
        for asset in ob:
            info = {'hostname': asset.hostname, 'ip': asset.ip}
            if asset.use_default_auth:
                if default:
                    info['port'] = default.default_port
                    info['username'] = default.default_user
                    info['password'] = default.default_password
                    info['ssh_key'] = default.default_pri_key_path
            else:
                info['port'] = asset.port
                info['username'] = asset.username
            res.append(info)
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
    rules_obj = role_obj.perm_rule.all()
    # 获取role 对应的用户 和 用户组
    # 获取role 对应的主机 和主机组
    users_obj = []
    assets_obj = []
    user_groups_obj = []
    group_users_obj = []
    asset_groups_obj = []
    group_assets_obj = []
    for rule in rules_obj:
        for user in rule.user.all():
            users_obj.append(user)
        for asset in rule.asset.all():
            assets_obj.append(asset)
        for user_group in rule.user_group.all():
            user_groups_obj.append(user_group)
            for user in user_group.user_set.all():
                group_users_obj.append(user)
        for asset_group in rule.asset_group.all():
            asset_groups_obj.append(asset_group)
            for asset in asset_group.asset_set.all():
                group_assets_obj.append(asset)

    calc_users = set(users_obj) | set(group_users_obj)
    calc_assets = set(assets_obj) | set(group_assets_obj)

    if type == "all":
        return {"rules": rules_obj,
                "users": list(calc_users),
                "user_groups": user_groups_obj,
                "assets": list(calc_assets),
                "asset_groups": asset_groups_obj,
                }
    elif type == "rule":
        return rules_obj
    elif type == "user":
        return calc_users
    elif type == "user_group":
        return user_groups_obj
    elif type == "asset":
        return calc_assets
    elif type == "asset_group":
        return asset_groups_obj
    else:
        return u"不支持的查询"


if __name__ == "__main__":
    print get_role_info(1)





