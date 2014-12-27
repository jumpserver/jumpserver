#coding: utf-8
import os
import django

os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings'
django.setup()
from juser.models import User, Group
from jasset.models import Asset, IDC
from jpermission.models import Permission

from connect import PyCrypt, KEY
cryptor = PyCrypt(KEY)


def add_group(name):
    group = Group(name=name)
    group.save()
    return group


def add_user(username, name, ldap_pwd='hadoop', ssh_key_pwd='hadoop',
             date_joined=0, role='CU', is_active=True, password='hadoop',):
    user = User(username=username, password=password, name=name, ldap_pwd=cryptor.encrypt(ldap_pwd),
                ssh_key_pwd=ssh_key_pwd, date_joined=date_joined, role=role, is_active=is_active)
    user.save()
    return user



def add_idc(name):
    idc = IDC(name=name)
    idc.save()
    return idc


def add_asset(ip, idc, password_common, port=2001, ldap_enable=False, username_common='guanghongwei', date_added=0):
    asset = Asset(ip=ip, idc=idc, password_common=password_common, port=port,
                  ldap_enable=ldap_enable, username_common=cryptor.encrypt(username_common), date_added=date_added)
    asset.save()
    return asset


def add_perm(user, asset, is_ldap, perm_user_type='C'):
    perm = Permission(user=user, asset=asset, is_ldap=is_ldap, perm_user_type=perm_user_type)
    perm.save()
    return perm


