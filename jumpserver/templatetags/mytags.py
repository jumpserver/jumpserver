# coding: utf-8

import re
import ast
import time

from django import template
from juser.models import User, UserGroup, DEPT
from jumpserver.api import *
from jasset.models import AssetAlias

register = template.Library()


@register.filter(name='stamp2str')
def stamp2str(value):
    try:
        return time.strftime('%Y/%m/%d %H:%M:%S', time.localtime(value))
    except AttributeError:
        return '0000/00/00 00:00:00'


@register.filter(name='int2str')
def int2str(value):
    return str(value)


@register.filter(name='get_role')
def get_role(user_id):
    user_role = {'SU': u'超级管理员', 'DA': u'部门管理员', 'CU': u'普通用户'}
    user = User.objects.filter(id=user_id)
    if user:
        user = user[0]
        return user_role.get(str(user.role), u"普通用户")
    else:
        return u"普通用户"


@register.filter(name='groups_str')
def groups_str(user_id):
    groups = []
    user = User.objects.get(id=user_id)
    for group in user.group.all():
        groups.append(group.name)
    if len(groups) < 3:
        return ' '.join(groups)
    else:
        return "%s ..." % ' '.join(groups[0:2])


@register.filter(name='group_str2')
def groups_str2(group_list):
    if len(group_list) < 3:
        return ' '.join([group.name for group in group_list])
    else:
        return '%s ...' % ' '.join([group.name for group in group_list[0:2]])


@register.filter(name='group_str2_all')
def groups_str2(group_list):
    group_lis = []
    for i in group_list:
        if str(i) != 'ALL':
            group_lis.append(i)
    if len(group_lis) < 3:
        return ' '.join([group.name for group in group_lis])
    else:
        return '%s ...' % ' '.join([group.name for group in group_lis[0:2]])


@register.filter(name='group_manage_str')
def group_manage_str(username):
    user = User.objects.get(username=username)
    group = user.user_group.filter(type='M')
    if group:
        return group[0].name
    else:
        return ''


@register.filter(name='get_item')
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter(name='bool2str')
def bool2str(value):
    if value:
        return u'是'
    else:
        return u'否'


@register.filter(name='user_readonly')
def user_readonly(user_id):
    user = User.objects.filter(id=user_id)
    if user:
        user = user[0]
        if user.role == 'CU':
            return False
    return True


@register.filter(name='member_count')
def member_count(group_id):
    group = UserGroup.objects.get(id=group_id)
    return group.user_set.count()


@register.filter(name='dept_user_num')
def dept_user_num(dept_id):
    dept = DEPT.objects.filter(id=dept_id)
    if dept:
        dept = dept[0]
        return dept.user_set.count()
    else:
        return 0


@register.filter(name='dept_group_num')
def dept_group_num(dept_id):
    dept = DEPT.objects.filter(id=dept_id)
    if dept:
        dept = dept[0]
        return dept.usergroup_set.all().count()
    else:
        return 0


@register.filter(name='perm_count')
def perm_count(group_id):
    group = UserGroup.objects.get(id=group_id)
    return group.perm_set.count()


@register.filter(name='dept_asset_num')
def dept_asset_num(dept_id):
    dept = DEPT.objects.filter(id=dept_id)
    if dept:
        dept = dept[0]
        return dept.asset_set.all().count()
    return 0


@register.filter(name='ugrp_perm_agrp_count')
def ugrp_perm_agrp_count(user_group_id):
    user_group = UserGroup.objects.filter(id=user_group_id)
    if user_group:
        user_group = user_group[0]
        return user_group.perm_set.all().count()
    return 0


@register.filter(name='ugrp_perm_asset_count')
def ugrp_perm_asset_count(user_group_id):
    user_group = UserGroup.objects.filter(id=user_group_id)
    assets = []
    if user_group:
        user_group = user_group[0]
        asset_groups = [perm.asset_group for perm in user_group.perm_set.all()]
        for asset_group in asset_groups:
            assets.extend(asset_group.asset_set.all())
    return len(set(assets))


@register.filter(name='get_user_alias')
def get_user_alias(post, user_id):
    user = User.objects.get(id=user_id)
    host = Asset.objects.get(id=post.id)
    alias = AssetAlias.objects.filter(user=user, host=host)
    if alias:
        return alias[0].alias
    else:
        return ''


@register.filter(name='group_type_to_str')
def group_type_to_str(type_name):
    group_types = {
        'P': '用户',
        'M': '部门',
        'A': '用户组',
    }
    return group_types.get(type_name)


@register.filter(name='ast_to_list')
def ast_to_list(lis):
    ast_lis = ast.literal_eval(lis)
    if len(ast_lis) <= 2:
        return ','.join([i for i in ast_lis])
    else:
        restr = ','.join([i for i in ast_lis[0:2]]) + '...'
        return restr


@register.filter(name='ast_to_list_1')
def ast_to_list_1(lis):
    return ast.literal_eval(lis)


@register.filter(name='string_length')
def string_length(string, length):
    return '%s ...' % string[0:length]


@register.filter(name='to_name')
def to_name(user_id):
    try:
        user = User.objects.filter(id=int(user_id))
        if user:
            user = user[0]
            return user.name
    except:
        return '非法用户'


@register.filter(name='to_role_name')
def to_role_name(role_id):
    role_dict = {'0': '普通用户', '1': '部门管理员', '2': '超级管理员'}
    return role_dict.get(str(role_id), '未知')


@register.filter(name='to_avatar')
def to_avatar(role_id='0'):
    role_dict = {'0': 'user', '1': 'admin', '2': 'root'}
    return role_dict.get(str(role_id), 'user')


@register.filter(name='get_user_asset_group')
def get_user_asset_group(user):
    return user_perm_group_api(user)
