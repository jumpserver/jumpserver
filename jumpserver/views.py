#coding: utf-8

import hashlib
import ldap
from ldap import modlist
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
from ConfigParser import ConfigParser
import os

from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect

from juser.models import User
from jasset.models import Asset, BisGroup, IDC

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
CONF = ConfigParser()
CONF.read(os.path.join(BASE_DIR, 'jumpserver.conf'))

LDAP_ENABLE = CONF.getint('ldap', 'ldap_enable')
if LDAP_ENABLE:
    LDAP_HOST_URL = CONF.get('ldap', 'host_url')
    LDAP_BASE_DN = CONF.get('ldap', 'base_dn')
    LDAP_ROOT_DN = CONF.get('ldap', 'root_dn')
    LDAP_ROOT_PW = CONF.get('ldap', 'root_pw')


def md5_crypt(string):
    return hashlib.new("md5", string).hexdigest()


def base(request):
    return render_to_response('base.html')


def skin_config(request):
    return render_to_response('skin_config.html')


def jasset_group_add(name, comment, type):
    if BisGroup.objects.filter(name=name):
        emg = u'该业务组已存在!'
    else:
        BisGroup.objects.create(name=name, comment=comment, type=type)
        smg = u'业务组%s添加成功' % name


class ServerError(Exception):
    pass


def page_list_return(total, current=1):
    min_page = current - 2 if current - 4 > 0 else 1
    max_page = min_page + 4 if min_page + 4 < total else total

    return range(min_page, max_page+1)


def jasset_host_edit(j_id, j_ip, j_idc, j_port, j_type, j_group, j_active, j_comment):
    groups = []
    is_active = {u'是': '1', u'否': '2'}
    login_types = {'LDAP': 'L', 'SSH_KEY': 'S', 'PASSWORD': 'P', 'MAP': 'M'}
    for group in j_group[0].split():
        print group.strip()
        c = BisGroup.objects.get(name=group.strip())
        groups.append(c)
    j_type = login_types[j_type]
    print j_type
    j_idc = IDC.objects.get(name=j_idc)
    print j_idc
    print
    a = Asset.objects.get(id=j_id)
    print '123'
    if j_type == 'M':
        a.ip = j_ip
        a.port = j_port
        a.login_type = j_type
        a.idc = j_idc
        a.is_active = j_active
        a.comment = j_comment
        a.username = j_user
        a.password = j_password
    else:
        a.ip = j_ip
        a.port = j_port
        a.idc = j_idc
        a.login_type = j_type
        a.is_active = is_active[j_active]
        a.comment = j_comment
    a.save()
    a.bis_group = groups
    a.save()


def login(request):
    """登录界面"""
    if request.session.get('username'):
        return HttpResponseRedirect('/')
    if request.method == 'GET':
        return render_to_response('login.html')
    else:
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = User.objects.filter(username=username)
        if user:
            user = user[0]
            if md5_crypt(password) == user.password:
                request.session['username'] = username
                if user.role == 'SU':
                    request.session['role'] = 2
                elif user.role == 'GA':
                    request.session['role'] = 1
                else:
                    request.session['role'] = 0
                return HttpResponseRedirect('/')
            else:
                error = '密码错误，请重新输入。'
        else:
            error = '用户不存在。'
    return render_to_response('login.html', {'error': error})


def logout(request):
    request.session.delete()
    return HttpResponseRedirect('/login/')


class LDAPMgmt():
    def __init__(self,
                 host_url,
                 base_dn,
                 root_cn,
                 root_pw):
        self.ldap_host = host_url
        self.ldap_base_dn = base_dn
        self.conn = ldap.initialize(host_url)
        self.conn.set_option(ldap.OPT_REFERRALS, 0)
        self.conn.protocol_version = ldap.VERSION3
        self.conn.simple_bind_s(root_cn, root_pw)

    def list(self, filter, scope=ldap.SCOPE_SUBTREE, attr=None):
        result = {}
        try:
            ldap_result = self.conn.search_s(self.ldap_base_dn, scope, filter, attr)
            for entry in ldap_result:
                name, data = entry
                for k, v in data.items():
                    print '%s: %s' % (k, v)
                    result[k] = v
            return result
        except ldap.LDAPError, e:
            print e

    def add(self, dn, attrs):
        try:
            ldif = modlist.addModlist(attrs)
            self.conn.add_s(dn, ldif)
        except ldap.LDAPError, e:
            print e

    def modify(self, dn, attrs):
        try:
            attr_s = []
            for k, v in attrs.items():
                attr_s.append((2, k, v))
            self.conn.modify_s(dn, attr_s)
        except ldap.LDAPError, e:
            print e

    def delete(self, dn):
        try:
            self.conn.delete_s(dn)
        except ldap.LDAPError, e:
            print e


class PyCrypt(object):
    """This class used to encrypt and decrypt password."""

    def __init__(self, key):
        self.key = key
        self.mode = AES.MODE_CBC

    def encrypt(self, text):
        cryptor = AES.new(self.key, self.mode, b'0000000000000000')
        length = 16
        try:
            count = len(text)
        except TypeError:
            raise ServerError('Encrypt password error, TYpe error.')
        add = (length - (count % length))
        text += ('\0' * add)
        ciphertext = cryptor.encrypt(text)
        return b2a_hex(ciphertext)

    def decrypt(self, text):
        cryptor = AES.new(self.key, self.mode, b'0000000000000000')
        try:
            plain_text = cryptor.decrypt(a2b_hex(text))
        except TypeError:
            raise ServerError('Decrypt password error, TYpe error.')
        return plain_text.rstrip('\0')


def perm_user_asset(user_id=None, username=None):
    if user_id:
        user = User.objects.get(id=user_id)
    else:
        user = User.objects.get(username=username)
    user_groups = user.user_group.all()
    perms = []
    assets = []
    asset_groups = []
    for user_group in user_groups:
        perm = user_group.perm_set.all()
        perms.extend(perm)

    for perm in perms:
        asset_groups.extend(perm.asset_group.all())

    for asset_group in asset_groups:
        assets.extend(list(asset_group.asset_set.all()))

    return assets


if LDAP_ENABLE:
    ldap_conn = LDAPMgmt(LDAP_HOST_URL, LDAP_BASE_DN, LDAP_ROOT_DN, LDAP_ROOT_PW)
else:
    ldap_conn = None



