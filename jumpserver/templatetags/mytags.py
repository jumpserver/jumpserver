# coding: utf-8

import time
from django import template
from juser.models import User

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
    return user_role.get(user.role)


@register.filter(name='groups_str')
def groups_str(username):
    groups = []
    user = User.objects.get(username=username)
    for group in user.user_group.all():
        groups.append(group.name)
    return ','.join(groups)

@register.filter(name='get_item')
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter(name='bool2str')
def bool2str(value):
    if value:
        return u'是'
    else:
        return u'否'

@register.filter(name='perm_total')
def perm_total(user_id):
    user = User.objects.get(int(user_id))
    return user.permission_set.all().count()