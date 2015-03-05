#coding: utf-8

import hashlib
import ldap
from ldap import modlist
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
from ConfigParser import ConfigParser
import os
import datetime
import json

from django.db.models import Count
from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.template import RequestContext

from juser.models import User
from jlog.models import Log
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


def getDaysByNum(num):
    today = datetime.date.today()
    oneday = datetime.timedelta(days=1)
    li_date, li_str = [], []
    for i in range(0, num):
        today = today-oneday
        li_date.append(today)
        li_str.append(str(today)[0:10])
    li_date.reverse()
    li_str.reverse()
    t = (li_date, li_str)
    return t


def base(request):
    return render_to_response('base.html', context_instance=RequestContext(request))


def index(request):
    path1, path2 = u'仪表盘', 'Dashboard'
    user_dic, host_dic = {}, {}
    li_date, li_str = getDaysByNum(7)
    today = datetime.datetime.now().day
    from_week = datetime.datetime.now() - datetime.timedelta(days=7)
    week_data = Log.objects.filter(start_time__range=[from_week, datetime.datetime.now()])
    user_top_ten = week_data.values('user').annotate(times=Count('user')).order_by('-times')[:10]
    host_top_ten = week_data.values('host').annotate(times=Count('host')).order_by('-times')[:10]
    for user in user_top_ten:
        username = user['user']
        li_user = []
        user_data = week_data.filter(user=username)
        for t in li_date:
            year, month, day = t.year, t.month, t.day
            times = user_data.filter(start_time__year=year, start_time__month=month, start_time__day=day).count()
            li_user.append(times)
        user_dic[username] = li_user

    for host in host_top_ten:
        ip = host['host']
        li_host = []
        host_data = week_data.filter(host=ip)
        for t in li_date:
            year, month, day = t.year, t.month, t.day
            times = host_data.filter(start_time__year=year, start_time__month=month, start_time__day=day).count()
            li_host.append(times)
        host_dic[ip] = li_host

    users = User.objects.all()
    hosts = Asset.objects.all()
    online_host = Log.objects.filter(is_finished=0)
    online_user = online_host.distinct()
    top_dic = {'活跃用户数': [8, 10, 5, 9, 8, 12, 3], '活跃主机数': [10, 16, 20, 8, 9, 5, 9], '登录次数': [20, 30, 35, 18, 40, 38, 65]}
    return render_to_response('index.html', locals(), context_instance=RequestContext(request))


def api_user(request):
    users = Log.objects.filter(is_finished=0).count()
    ret = {'users': users}
    return HttpResponse(json.dumps(ret))


def skin_config(request):
    return render_to_response('skin_config.html')


def jasset_group_add(name, comment, jtype):
    if BisGroup.objects.filter(name=name):
        emg = u'该业务组已存在!'
    else:
        BisGroup.objects.create(name=name, comment=comment, type=jtype)
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
        c = BisGroup.objects.get(name=group.strip())
        groups.append(c)
    j_type = login_types[j_type]
    j_idc = IDC.objects.get(name=j_idc)
    a = Asset.objects.get(id=j_id)
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


def pages(posts, r):
    """分页公用函数"""
    contact_list = posts
    p = paginator = Paginator(contact_list, 20)
    try:
        current_page = int(r.GET.get('page', '1'))
    except ValueError:
        current_page = 1

    page_range = page_list_return(len(p.page_range), current_page)

    try:
        contacts = paginator.page(current_page)
    except (EmptyPage, InvalidPage):
        contacts = paginator.page(paginator.num_pages)

    return contact_list, p, contacts, page_range, current_page


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
                request.session['user_id'] = user.id
                if user.role == 'SU':
                    request.session['role_id'] = 2
                elif user.role == 'GA':
                    request.session['role_id'] = 1
                else:
                    request.session['role_id'] = 0
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



