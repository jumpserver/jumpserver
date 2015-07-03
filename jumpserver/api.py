# coding: utf-8


from django.http import HttpResponseRedirect
import json
import os
from ConfigParser import ConfigParser
import getpass
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
import ldap
from ldap import modlist
import hashlib
import datetime
import random
import subprocess
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response
from juser.models import User, UserGroup, DEPT
from jasset.models import Asset, BisGroup, IDC
from jlog.models import Log
from jasset.models import AssetAlias
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import send_mail
import json
import logging


BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
CONF = ConfigParser()
CONF.read(os.path.join(BASE_DIR, 'jumpserver.conf'))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
JLOG_FILE = os.path.join(LOG_DIR, 'jumpserver.log')
SSH_KEY_DIR = os.path.join(BASE_DIR, 'keys')
# SERVER_KEY_DIR = os.path.join(SSH_KEY_DIR, 'server')
KEY = CONF.get('base', 'key')
LOGIN_NAME = getpass.getuser()
LDAP_ENABLE = CONF.getint('ldap', 'ldap_enable')
SEND_IP = CONF.get('base', 'ip')
SEND_PORT = CONF.get('base', 'port')
MAIL_FROM = CONF.get('mail', 'email_host_user')

log_level = CONF.get('base', 'log')
log_level_total = {'debug': logging.DEBUG, 'info': logging.INFO, 'warning': logging.WARN, 'error': logging.ERROR,
                   'critical': logging.CRITICAL}
logger = logging.getLogger('jumpserver')
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(JLOG_FILE)
fh.setLevel(log_level_total.get(log_level, logging.DEBUG))
formatter = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)


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


def page_list_return(total, current=1):
    min_page = current - 2 if current - 4 > 0 else 1
    max_page = min_page + 4 if min_page + 4 < total else total

    return range(min_page, max_page+1)


def pages(posts, r):
    """分页公用函数"""
    contact_list = posts
    p = paginator = Paginator(contact_list, 10)
    try:
        current_page = int(r.GET.get('page', '1'))
    except ValueError:
        current_page = 1

    page_range = page_list_return(len(p.page_range), current_page)

    try:
        contacts = paginator.page(current_page)
    except (EmptyPage, InvalidPage):
        contacts = paginator.page(paginator.num_pages)

    if current_page >= 5:
        show_first = 1
    else:
        show_first = 0
    if current_page <= (len(p.page_range) - 3):
        show_end = 1
    else:
        show_end = 0

    return contact_list, p, contacts, page_range, current_page, show_first, show_end


class PyCrypt(object):
    """
    This class used to encrypt and decrypt password.
    对称加密库
    """

    def __init__(self, key):
        self.key = key
        self.mode = AES.MODE_CBC

    @staticmethod
    def random_pass():
        """
        random password
        随机生成密码
        """
        salt_key = '1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!@$%^&*()_'
        symbol = '!@$%^&*()_'
        salt_list = []
        for i in range(60):
            salt_list.append(random.choice(salt_key))
        for i in range(4):
            salt_list.append(random.choice(symbol))
        salt = ''.join(salt_list)
        return salt

    @staticmethod
    def md5_crypt(string):
        return hashlib.new("md5", string).hexdigest()

    def encrypt(self, passwd=None):
        """
        encrypt gen password
        加密生成密码
        """
        if not passwd:
            passwd = self.random_pass()

        cryptor = AES.new(self.key, self.mode, b'8122ca7d906ad5e1')
        length = 64
        try:
            count = len(passwd)
        except TypeError:
            raise ServerError('Encrypt password error, TYpe error.')

        add = (length - (count % length))
        passwd += ('\0' * add)
        cipher_text = cryptor.encrypt(passwd)
        return b2a_hex(cipher_text)

    def decrypt(self, text):
        cryptor = AES.new(self.key, self.mode, b'8122ca7d906ad5e1')
        try:
            plain_text = cryptor.decrypt(a2b_hex(text))
        except TypeError:
            # raise ServerError('Decrypt password error, TYpe error.')
            pass
        return plain_text.rstrip('\0')


class ServerError(Exception):
    pass


def get_object(model, **kwargs):
    try:
        the_object = model.objects.get(**kwargs)
    except ObjectDoesNotExist:
        raise ServerError('Object get %s failed.' % str(kwargs.values()))
    return the_object


def require_login(func):
    """要求登录的装饰器"""
    def _deco(request, *args, **kwargs):
        if not request.session.get('user_id'):
            return HttpResponseRedirect('/login/')
        return func(request, *args, **kwargs)
    return _deco


def require_super_user(func):
    def _deco(request, *args, **kwargs):
        if not request.session.get('user_id'):
            return HttpResponseRedirect('/login/')

        if request.session.get('role_id', 0) != 2:
            return HttpResponseRedirect('/')
        return func(request, *args, **kwargs)
    return _deco


def require_admin(func):
    def _deco(request, *args, **kwargs):
        if not request.session.get('user_id'):
            return HttpResponseRedirect('/login/')

        if request.session.get('role_id', 0) < 1:
            return HttpResponseRedirect('/')
        return func(request, *args, **kwargs)
    return _deco


def is_super_user(request):
    if request.session.get('role_id') == 2:
        return True
    else:
        return False


def is_group_admin(request):
    if request.session.get('role_id') == 1:
        return True
    else:
        return False


def is_common_user(request):
    if request.session.get('role_id') == 0:
        return True
    else:
        return False


@require_login
def get_session_user_dept(request):
    user_id = request.session.get('user_id', 0)
    user = User.objects.filter(id=user_id)
    if user:
        user = user[0]
        dept = user.dept
        return user, dept


@require_login
def get_session_user_info(request):
    user_id = request.session.get('user_id', 0)
    user = User.objects.filter(id=user_id)
    if user:
        user = user[0]
        dept = user.dept
        return [user.id, user.username, user, dept.id, dept.name, dept]


def get_user_dept(request):
    user_id = request.session.get('user_id')
    if user_id:
        user_dept = User.objects.get(id=user_id).dept
        return user_dept.id


def api_user(request):
    hosts = Log.objects.filter(is_finished=0).count()
    users = Log.objects.filter(is_finished=0).values('user').distinct().count()
    ret = {'users': users, 'hosts': hosts}
    json_data = json.dumps(ret)
    return HttpResponse(json_data)


# def view_splitter(request, su=None, adm=None):
#     if is_super_user(request):
#         return su(request)
#     elif is_group_admin(request):
#         return adm(request)
#     else:
#         return HttpResponseRedirect('/login/')


# def user_group_perm_asset_group_api(user_group):
#     asset_group_list = []
#     perm_list = user_group.perm_set.all()
#     for perm in perm_list:
#         asset_group_list.append(perm.asset_group)
#     return asset_group_list


class Juser(object):
    """
    Jumpserver user class
    用户类
    """

    def __init__(self, username=None, uid=None):
        if username:
            user = User.objects.filter(username=username)
        elif uid:
            user = User.objects.filter(id=uid)
        else:
            user = ''

        if user:
            user = user[0]
            self.user = user
            self.id = user.id
            # self.id = user.id
            # self.username = user.username
            # self.name = user.name
            self.group = user.group.all()
        else:
            self.id = None

    def __repr__(self):
        if self.id:
            return '<%s Juser instance>' % getattr(self.user, 'username')
        else:
            return 'None'

    def __getattr__(self, item):
        if self.id:
            return getattr(self.user, item)
        else:
            return None

    def validate(self):
        """
        Validate is or not a true user
        鉴定用户
        """
        if self.id:
            return True
        else:
            return False

    def get_asset_group(self):
        """
        Get user host_groups.
        获取用户有权限的主机组
        """
        host_group_list = []
        perm_list = []
        user_group_all = self.user.group.all()
        for user_group in user_group_all:
            perm_list.extend(user_group.perm_set.all())

        for perm in perm_list:
            host_group_list.append(perm.asset_group)

        return host_group_list

    def get_asset_group_info(self, printable=False):
        """
        Get or print asset group info
        获取或打印用户授权资产组
        """
        asset_groups_info = {}
        asset_groups = self.get_asset_group()

        for asset_group in asset_groups:
            asset_groups_info[asset_group.id] = [asset_group.name, asset_group.comment]

        if printable:
            for group_id in asset_groups_info:
                if asset_groups_info[group_id][1]:
                    print "[%3s] %s -- %s" % (group_id,
                                              asset_groups_info[group_id][0],
                                              asset_groups_info[group_id][1])
                else:
                    print "[%3s] %s" % (group_id, asset_groups_info[group_id][0])
                print ''
        else:
            return asset_groups_info

    def get_asset(self):
        """
        Get the assets of under the user control.
        获取主机列表
        """
        assets = []
        asset_groups = self.get_asset_group()

        for asset_group in asset_groups:
            assets.extend(asset_group.asset_set.all())

        return assets

    def get_asset_info(self, printable=False):
        """
        Get or print the user asset info
        获取或打印用户资产信息
        """
        assets_info = {}
        assets = self.get_asset()

        for asset in assets:
            asset_alias = AssetAlias.objects.filter(user=self.user, asset=asset)
            if asset_alias and asset_alias[0].alias != '':
                assets_info[asset.ip] = [asset.id, asset.ip, str(asset_alias[0].alias)]
            else:
                assets_info[asset.ip] = [asset.id, asset.ip, str(asset.comment)]

        if printable:
            ips = assets_info.keys()
            ips.sort()
            for ip in ips:
                if assets_info[ip][2]:
                    print '%-15s -- %s' % (ip, assets_info[ip][2])
                else:
                    print '%-15s' % ip
            print ''
        else:
            return assets_info


class Jasset(object):
    """
    Jumpserver asset class
    Jumpserver资产类
    """
    def __init__(self, ip=None, id=None):
        if ip:
            asset = Asset.objects.filter(ip=ip)
        elif id:
            asset = Asset.objects.filter(id=id)
        else:
            asset = ''

        if asset:
            asset = asset[0]
            self.asset = asset
            self.id = asset.id
        else:
            self.id = None

    def __repr__(self):
        if self.id:
            return '<%s Jasset instance>' % self.asset.ip
        else:
            return 'None'

    def __getattr__(self, item):
        if self.id:
            return getattr(self.asset, item)
        else:
            return None

    def validate(self):
        """
        Validate is or not a true asset
        判断是否存在
        """
        if self.id:
            return True
        else:
            return False

    def get_user(self):
        perm_list = []
        asset_group_all = self.asset.bis_group.all()
        for asset_group in asset_group_all:
            perm_list.extend(asset_group.perm_set.all())

        user_group_list = []
        for perm in perm_list:
            user_group_list.append(perm.user_group)

        user_permed_list = []
        for user_group in user_group_list:
            user_permed_list.extend(user_group.user_set.all())
        user_permed_list = list(set(user_permed_list))
        return user_permed_list


class JassetGroup(object):
    """
    Jumpserver AssetGroup class
    Jumpserver 资产组类
    """
    def __init__(self, name=None, id=None):
        if id:
            asset_group = BisGroup.objects.filter(id=int(id))
        elif name:
            asset_group = BisGroup.objects.filter(name=name)
        else:
            asset_group = ''

        if asset_group:
            asset_group = asset_group[0]
            self.asset_group = asset_group
            # self.name = asset_group.name
            self.id = asset_group.id
        else:
            self.id = None

    def __repr__(self):
        if self.id:
            return '<%s JassetGroup instance>' % self.name
        else:
            return 'None'

    def validate(self):
        """
        Validate it is a true asset group or not
        鉴定是否为真是存在的组
        """
        if self.id:
            return True
        else:
            return False

    def get_asset(self):
        return self.asset_group.asset_set.all()

    def get_asset_info(self, printable=False):
        assets = self.get_asset()
        for asset in assets:
            if asset.comment:
                print '%-15s -- %s' % (asset.ip, asset.comment)
            else:
                print '%-15s' % asset.ip
        print ''

    def get_asset_num(self):
        return len(self.get_asset())

    def get_user_group(self):
        perm_list = self.asset_group.perm_set.all()
        user_group_list = []
        for perm in perm_list:
            user_group_list.append(perm.user_group)
        return user_group_list

    def get_user(self):
        user_list = []
        user_group_list = self.get_user_group()
        for user_group in user_group_list:
            user_list.extend(user_group.user_set.all())
        return user_list

    def is_permed(self, user=None, user_group=None):
        if user:
            if user in self.get_user():
                return True

        if user_group:
            if user_group in self.get_user_group():
                return True
        return False


# def asset_perm_api(asset):
#     if asset:
#         perm_list = []
#         asset_group_all = asset.bis_group.all()
#         for asset_group in asset_group_all:
#             perm_list.extend(asset_group.perm_set.all())
#
#         user_group_list = []
#         for perm in perm_list:
#             user_group_list.append(perm.user_group)
#
#         user_permed_list = []
#         for user_group in user_group_list:
#             user_permed_list.extend(user_group.user_set.all())
#         user_permed_list = list(set(user_permed_list))
#         return user_permed_list


def validate(request, user_group=None, user=None, asset_group=None, asset=None, edept=None):
    dept = get_session_user_dept(request)[1]
    if edept:
        if dept.id != int(edept[0]):
            return False
        
    if user_group:
        dept_user_groups = dept.usergroup_set.all()
        user_group_ids = []
        for group in dept_user_groups:
            user_group_ids.append(str(group.id))

        if not set(user_group).issubset(set(user_group_ids)):
            return False

    if user:
        dept_users = dept.user_set.all()
        user_ids = []
        for dept_user in dept_users:
            user_ids.append(str(dept_user.id))

        if not set(user).issubset(set(user_ids)):
            return False

    if asset_group:
        dept_asset_groups = dept.bisgroup_set.all()
        asset_group_ids = []
        for group in dept_asset_groups:
            asset_group_ids.append(str(group.id))

        if not set(asset_group).issubset(set(asset_group_ids)):
            return False

    if asset:
        dept_assets = dept.asset_set.all()
        asset_ids = []
        for dept_asset in dept_assets:
            asset_ids.append(str(dept_asset.id))

        if not set(asset).issubset(set(asset_ids)):
            return False

    return True


def verify(request, user_group=None, user=None, asset_group=None, asset=None, edept=None):
    dept = get_session_user_dept(request)[1]
    if edept:
        if dept.id != int(edept[0]):
            return False

    if user_group:
        dept_user_groups = dept.usergroup_set.all()
        user_groups = []
        for user_group_id in user_group:
            user_groups.extend(UserGroup.objects.filter(id=user_group_id))
        if not set(user_groups).issubset(set(dept_user_groups)):
            return False

    if user:
        dept_users = dept.user_set.all()
        users = []
        for user_id in user:
            users.extend(User.objects.filter(id=user_id))

        if not set(users).issubset(set(dept_users)):
            return False

    if asset_group:
        dept_asset_groups = dept.bisgroup_set.all()
        asset_group_ids = []
        for group in dept_asset_groups:
            asset_group_ids.append(str(group.id))

        if not set(asset_group).issubset(set(asset_group_ids)):
            return False

    if asset:
        dept_assets = dept.asset_set.all()
        asset_ids = []
        for a in dept_assets:
            asset_ids.append(str(a.id))
        print asset, asset_ids
        if not set(asset).issubset(set(asset_ids)):
            return False

    return True


def bash(cmd):
    """执行bash命令"""
    return subprocess.call(cmd, shell=True)


def is_dir(dir_name, username='root', mode=0755):
    if not os.path.isdir(dir_name):
        os.makedirs(dir_name)
        bash("chown %s:%s '%s'" % (username, username, dir_name))
    os.chmod(dir_name, mode)


def http_success(request, msg):
    return render_to_response('success.html', locals())


def http_error(request, emg):
    message = emg
    return render_to_response('error.html', locals())


CRYPTOR = PyCrypt(KEY)

if LDAP_ENABLE:
    LDAP_HOST_URL = CONF.get('ldap', 'host_url')
    LDAP_BASE_DN = CONF.get('ldap', 'base_dn')
    LDAP_ROOT_DN = CONF.get('ldap', 'root_dn')
    LDAP_ROOT_PW = CONF.get('ldap', 'root_pw')
    ldap_conn = LDAPMgmt(LDAP_HOST_URL, LDAP_BASE_DN, LDAP_ROOT_DN, LDAP_ROOT_PW)
else:
    ldap_conn = None

