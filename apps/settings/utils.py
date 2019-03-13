# -*- coding: utf-8 -*-
#

from django.db.models import Q
from ldap3 import Server, Connection
from rest_framework.views import Response
from django.utils.translation import ugettext_lazy as _

from .models import settings
from users.models import User


def ldap_conn(host, use_ssl, bind_dn, password):
    server = Server(host, use_ssl=use_ssl)
    conn = Connection(server, bind_dn, password)
    return conn


def ldap_bind(conn):
    try:
        conn.bind()
    except Exception as e:
        return Response({"error": str(e)}, status=401)


def ldap_search(conn, search_ougroup, search_filter, attr_map, user_names=None):
    users = []
    for search_ou in str(search_ougroup).split("|"):
        ok = conn.search(search_ou, search_filter % ({"user": "*"}),
                         attributes=list(attr_map.values())
                         )
        if not ok:
            return {"error": _(
                "Search no entry matched in ou {}").format(search_ou)}
        for entry in conn.entries:
            user = {}
            for attr, mapping in attr_map.items():
                if hasattr(entry, mapping):
                    value = getattr(entry, mapping).value
                    user[attr] = value if value else ''
            if user_names:
                if user.get('username', '') in user_names:
                        users.append(user)
            else:
                users.append(user)
    if len(users) > 0:
        return users
    else:
        return {"error": "Have user but attr mapping error"}


def get_ldap_setting():
    host = settings.AUTH_LDAP_SERVER_URI
    bind_dn = settings.AUTH_LDAP_BIND_DN
    password = settings.AUTH_LDAP_BIND_PASSWORD
    use_ssl = settings.AUTH_LDAP_START_TLS
    search_ougroup = settings.AUTH_LDAP_SEARCH_OU
    search_filter = settings.AUTH_LDAP_SEARCH_FILTER
    attr_map = settings.AUTH_LDAP_USER_ATTR_MAP
    auth_ldap = settings.AUTH_LDAP

    if not host:
        return Response({'error': _("请设置Ldap站点地址并提交")}, status=401)
    if not password:
        return Response({'error': _("请设置Ldap密码并提交")}, status=401)
    if not bind_dn:
        return Response({'error': _("请设置Ldap的DN并提交")}, status=401)
    if not search_ougroup:
        return Response({'error': _("请设置Ldap的用户OU并提交")}, status=401)
    if not search_filter:
        return Response({'error': _("请先设置Ldap用户过滤器并提交")}, status=401)
    if not attr_map:
        return Response({'error': _("请先设置Ldap属性映射并提交")}, status=401)
    if not auth_ldap:
        return Response({'error': _("请先勾选启用LDAP认证")}, status=401)

    ldap_setting = {
        'host': host, 'bind_dn': bind_dn, 'password': password,
        'search_ougroup': search_ougroup, 'search_filter': search_filter,
        'attr_map': attr_map, 'auth_ldap': auth_ldap, 'use_ssl': use_ssl,
    }
    return ldap_setting


def save_user(users):
    if len(users) > 0:
        exist = []
        for item in users:
            if not item.get('email', ''):
                item['email'] = item['username'] + '@' + item[
                    'username'] + '.com'
            item['source'] = 'ldap'
            user = User.objects.filter(
                Q(username=item['username']) & ~Q(source='ldap'))
            if user:
                exist.append(item['username'])
                continue
            user = User.objects.filter(username=item['username'], source='ldap')
            if user:
                user = user[0]
                for key, value in item.items():
                    user.key = value
                    user.save()
            else:
                try:
                    user = User.objects.create(**item)
                except:

                    exist.append(item['username'])
                    continue
        if exist:
            msg = _("导入 {} 个用户成功, 导入 {} 这些用户失败，数据库已经存在同名的用户")\
                .format(len(users) - len(exist), str(exist))
        else:
            msg = _("导入 {} 个用户成功").format(len(users))
        return Response(
            {"msg": msg})
    else:
        return Response({"error": "Have user but attr mapping error"},
                        status=401)








