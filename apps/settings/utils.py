# -*- coding: utf-8 -*-
#

from ldap3 import Server, Connection
from django.utils.translation import ugettext_lazy as _

from .models import settings
from users.models import User


def ldap_conn(host, use_ssl, bind_dn, password):
    server = Server(host, use_ssl=use_ssl)
    conn = Connection(server, bind_dn, password)
    return conn


def ldap_search(conn, search_ougroup, search_filter, attr_map, user_names=None):
    users_list = []
    for search_ou in str(search_ougroup).split("|"):
        ok = conn.search(search_ou, search_filter % ({"user": "*"}),
                         attributes=list(attr_map.values()))
        if not ok:
            error = _("Search no entry matched in ou {}").format(search_ou)
            return {"error": error}

        ldap_map_users(conn, attr_map, users_list, user_names)

    if len(users_list) > 0:
        return users_list
    return {"error": _("Have user but attr mapping error")}


def get_ldap_users_list(user_names=None):
    ldap_setting = get_ldap_setting()
    conn = ldap_conn(ldap_setting['host'], ldap_setting['use_ssl'],
                     ldap_setting['bind_dn'], ldap_setting['password'])
    try:
        conn.bind()
    except Exception as e:
        return {"error": str(e)}

    result_search = ldap_search(conn, ldap_setting['search_ougroup'],
                                ldap_setting['search_filter'],
                                ldap_setting['attr_map'], user_names=user_names)
    return result_search


def ldap_map_users(conn, attr_map, users, user_names=None):
    for entry in conn.entries:
        user = entry_user(entry, attr_map)
        if user_names:
            if user.get('username', '') in user_names:
                users.append(user)
        else:
            users.append(user)


def entry_user(entry, attr_map):
    user = {}
    user['is_imported'] = _('No')
    for attr, mapping in attr_map.items():
        if not hasattr(entry, mapping):
            continue
        value = getattr(entry, mapping).value
        user[attr] = value if value else ''
        if attr != 'username':
            continue
        if User.objects.filter(username=user[attr]):
            user['is_imported'] = _('Yes')
    return user


def get_ldap_setting():
    host = settings.AUTH_LDAP_SERVER_URI
    bind_dn = settings.AUTH_LDAP_BIND_DN
    password = settings.AUTH_LDAP_BIND_PASSWORD
    use_ssl = settings.AUTH_LDAP_START_TLS
    search_ougroup = settings.AUTH_LDAP_SEARCH_OU
    search_filter = settings.AUTH_LDAP_SEARCH_FILTER
    attr_map = settings.AUTH_LDAP_USER_ATTR_MAP
    auth_ldap = settings.AUTH_LDAP

    ldap_setting = {
        'host': host, 'bind_dn': bind_dn, 'password': password,
        'search_ougroup': search_ougroup, 'search_filter': search_filter,
        'attr_map': attr_map, 'auth_ldap': auth_ldap, 'use_ssl': use_ssl,
    }
    return ldap_setting


def save_user(users):
    exist = []
    username_list = [item.get('username') for item in users]
    for name in username_list:
        if User.objects.filter(username=name).exclude(source='ldap'):
            exist.append(name)
    users = [user for user in users if (user.get('username') not in exist)]

    result_save = save(users, exist)
    return result_save


def save(users, exist):
    fail_user = []
    for item in users:
        item = set_default_item(item)
        user = User.objects.filter(username=item['username'], source='ldap')
        user = user.first()
        if not user:
            try:
                user = User.objects.create(**item)
            except Exception as e:
                fail_user.append(item.get('username'))
                continue
        for key, value in item.items():
            user.key = value
            user.save()

    get_msg = get_messages(users, exist, fail_user)
    return get_msg


def set_default_item(item):
    item['source'] = 'ldap'
    if not item.get('email', ''):
        if '@' in item['username']:
            item['email'] = item['username']
        else:
            item['email'] = item['username'] + '@' + settings.EMAIL_SUFFIX
    if 'is_imported' in item.keys():
        item.pop('is_imported')
    return item


def get_messages(users, exist, fail_user):
    if exist:
        info = _("Import {} users successfully; import {} users failed, the "
                 "database already exists with the same name")
        msg = info.format(len(users), str(exist))

        if fail_user:
            info = _("Import {} users successfully; import {} users failed, "
                     "the database already exists with the same name; import {}"
                     "users failed, Because’TypeError' object has no attribute "
                     "'keys'")
            msg = info.format(len(users)-len(fail_user), str(exist), str(fail_user))
    else:
        msg = _("Import {} users successfully").format(len(users))

        if fail_user:
            info = _("Import {} users successfully;import {} users failed, "
                     "Because’TypeError' object has no attribute 'keys'")
            msg = info.format(len(users)-len(fail_user), str(fail_user))
    return {'msg': msg}