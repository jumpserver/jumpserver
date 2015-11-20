# coding: utf-8


from jumpserver.api import *
import uuid
import re

from jumpserver.models import Setting
from jperm.models import PermRole
from jperm.models import PermRule


class PermGet(object):
    def __init__(self):
        pass


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





