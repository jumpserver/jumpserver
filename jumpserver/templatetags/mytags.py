# coding: utf-8

import time
import re
from django import template
from django.db.models import Q
from juser.models import User, UserGroup
from jperm.views import perm_user_asset
from jasset.models import BisGroup

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
    user_role = {'SU': u'超级管理员', 'GA': u'组管理员', 'CU': u'普通用户'}
    user = User.objects.get(id=user_id)
    return user_role.get(str(user.role))


@register.filter(name='groups_str')
def groups_str(username):
    groups = []
    user = User.objects.get(username=username)
    for group in user.user_group.filter(type='A'):
        groups.append(group.name)
    if len(groups) < 4:
        return ' '.join(groups)
    else:
        return "%s ..." % ' '.join(groups[0:3])


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


@register.filter(name='member_count')
def member_count(group_id):
    group = UserGroup.objects.get(id=group_id)
    return group.user_set.count()


@register.filter(name='perm_count')
def perm_count(group_id):
    group = UserGroup.objects.get(id=group_id)
    return group.perm_set.count()


@register.filter(name='group_type_to_str')
def group_type_to_str(type_name):
    group_types = {
        'P': '用户',
        'M': '部门',
        'A': '用户组',
    }
    return group_types.get(type_name)


@register.filter(name='perm_asset_count')
def perm_asset_count(user_id):
    return len(perm_user_asset(user_id))


@register.filter(name='filter_private')
def filter_private(group):
    agroup = []
    pattern = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
    p = BisGroup.objects.get(name='ALL')
    for g in group:
        if not pattern.match(g.name):
            agroup.append(g)
    try:
        agroup.remove(p)
    except ValueError:
        pass

    return agroup
