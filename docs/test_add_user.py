#coding: utf-8
import os
import django

os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings'
django.setup()
from juser.models import User, Group
from jasset.models import Asset, IDC
from jpermission.models import Permission


def add_group(group):
    group = Group(name='hadoop')
    group.save()
    return group


def add_user(username, name,  group, ldap_pwd='hadoop', ssh_key_pwd='hadoop',
             date_joined=0, role='CU', is_active=True, password='hadoop',):
    user = User(username=username, password=password, name=name, group=group, ldap_pwd=ldap_pwd,
                ssh_key_pwd=ssh_key_pwd, date_joined=date_joined, role=role, is_active=is_active)
    user.save()
    return user


def add_idc(name):
    idc = IDC(name=name)
    idc.save()
    return idc


def add_asset(ip, idc, password_common, port=2001, ldap_enable=False, username_common='guanghongwei', date_add=0):
    asset = Asset(ip=ip, idc=idc, password_common=password_common, port=port,
                  ldap_enable=ldap_enable, username_common=username_common, date_add=date_add)
    asset.save()
    return asset


def add_perm(user, asset, is_ldap, perm_user_type='C'):
    perm = Permission(user, asset, is_ldap, perm_user_type)
    perm.save()
    return perm


wrm = add_group('wrm')
guanghongwei = add_user('guanghongwei', 'guanghongwei', wrm)

sd = add_idc('sd')
test1 = add_asset('172.16.1.122', sd, 'Lov@j1ax1n')

perm = add_perm(guanghongwei, test1, is_ldap=False)






