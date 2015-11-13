# coding: utf-8

import re
import ast
import time

from django import template
# from jperm.models import CmdGroup
from jumpserver.api import *
from jasset.models import AssetAlias

register = template.Library()


@register.filter(name='int2str')
def int2str(value):
    """
    int 转换为 str
    """
    return str(value)


@register.filter(name='get_role')
def get_role(user_id):
    """
    根据用户id获取用户权限
    """

    user_role = {'SU': u'超级管理员', 'GA': u'组管理员', 'CU': u'普通用户'}
    user = get_object(User, id=user_id)
    if user:
        return user_role.get(str(user.role), u"普通用户")
    else:
        return u"普通用户"


@register.filter(name='groups2str')
def groups2str(group_list):
    """
    将用户组列表转换为str
    """
    if len(group_list) < 3:
        return ' '.join([group.name for group in group_list])
    else:
        return '%s ...' % ' '.join([group.name for group in group_list[0:2]])


@register.filter(name='user_asset_count')
def user_asset_count(user):
    """
    返回用户权限主机的数量
    """
    assets = user.asset.all()
    asset_groups = user.asset_group.all()

    for asset_group in asset_groups:
        if asset_group:
            assets.extend(asset_group.asset_set.all())

    return len(assets)


@register.filter(name='user_asset_group_count')
def user_asset_group_count(user):
    """
    返回用户权限主机组的数量
    """
    return len(user.asset_group.all())


@register.filter(name='bool2str')
def bool2str(value):
    if value:
        return u'是'
    else:
        return u'否'


@register.filter(name='members_count')
def members_count(group_id):
    """统计用户组下成员数量"""
    group = get_object(UserGroup, id=group_id)
    if group:
        return group.user_set.count()
    else:
        return 0


@register.filter(name='to_name')
def to_name(user_id):
    """user id 转位用户名称"""
    try:
        user = User.objects.filter(id=int(user_id))
        if user:
            user = user[0]
            return user.name
    except:
        return '非法用户'


@register.filter(name='to_role_name')
def to_role_name(role_id):
    """role_id 转变为角色名称"""
    role_dict = {'0': '普通用户', '1': '组管理员', '2': '超级管理员'}
    return role_dict.get(str(role_id), '未知')


@register.filter(name='to_avatar')
def to_avatar(role_id='0'):
    """不同角色不同头像"""
    role_dict = {'0': 'user', '1': 'admin', '2': 'root'}
    return role_dict.get(str(role_id), 'user')


@register.filter(name='result2bool')
def result2bool(result=''):
    """将结果定向为结果"""
    result = eval(result)
    unreachable = result.get('unreachable', [])
    failures = result.get('failures', [])

    if unreachable or failures:
        return '<b style="color: red">失败</b>'
    else:
        return '<b style="color: green">成功</b>'


@register.filter(name='rule_member_count')
def rule_member_count(instance, member):
    """
    instance is a rule object,
    use to get the number of the members
    :param instance:
    :param member:
    :return:
    """
    member = getattr(instance, member)
    counts = member.all().count()
    return str(counts)


@register.filter(name='rule_member_name')
def rule_member_name(instance, member):
    """
    instance is a rule object,
    use to get the name of the members
    :param instance:
    :param member:
    :return:
    """
    member = getattr(instance, member)
    names = member.all()

    return names


@register.filter(name='user_which_groups')
def user_which_group(user, member):
    """
    instance is a user object,
    use to get the group of the user
    :param instance:
    :param member:
    :return:
    """
    member = getattr(user, member)
    names = [members.name for members in member.all()]

    return ','.join(names)


@register.filter(name='asset_which_groups')
def asset_which_group(asset, member):
    """
    instance is a user object,
    use to get the group of the user
    :param instance:
    :param member:
    :return:
    """
    member = getattr(asset, member)
    names = [members.name for members in member.all()]

    return ','.join(names)
