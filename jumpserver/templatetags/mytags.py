import time
from django import template

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


@register.filter(name='get_value')
def get_value(dicts, key):
    return dicts.get(key, '')

@register.filter(name='groups_str')
def groups_str(group_list):
    groups = []
    for group in group_list:
        groups.append(group.name)
    return ','.join(groups)