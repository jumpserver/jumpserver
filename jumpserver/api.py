# coding: utf-8

import os, sys, time, re
from Crypto.Cipher import AES
import crypt
import pwd
from binascii import b2a_hex, a2b_hex
import hashlib
import datetime
import random
import subprocess
import uuid
import json
import logging

from settings import *
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.http import HttpResponse, Http404
from django.template import RequestContext
from juser.models import User, UserGroup
from jlog.models import Log, TtyLog
from jasset.models import Asset, AssetGroup
from jperm.models import PermRule, PermRole
from jumpserver.models import Setting
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.core.mail import send_mail
from django.core.urlresolvers import reverse


def set_log(level, filename='jumpserver.log'):
    """
    return a log file object
    根据提示设置log打印
    """
    log_file = os.path.join(LOG_DIR, filename)
    if not os.path.isfile(log_file):
        os.mknod(log_file)
        os.chmod(log_file, 0777)
    log_level_total = {'debug': logging.DEBUG, 'info': logging.INFO, 'warning': logging.WARN, 'error': logging.ERROR,
                       'critical': logging.CRITICAL}
    logger_f = logging.getLogger('jumpserver')
    logger_f.setLevel(logging.DEBUG)
    fh = logging.FileHandler(log_file)
    fh.setLevel(log_level_total.get(level, logging.DEBUG))
    formatter = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger_f.addHandler(fh)
    return logger_f


def list_drop_str(a_list, a_str):
    for i in a_list:
        if i == a_str:
            a_list.remove(a_str)
    return a_list


def get_asset_info(asset):
    """
    获取资产的相关管理账号端口等信息
    """
    default = get_object(Setting, name='default')
    info = {'hostname': asset.hostname, 'ip': asset.ip}
    if asset.use_default_auth:
        if default:
            info['username'] = default.field1
            try:
                info['password'] = CRYPTOR.decrypt(default.field3)
            except ServerError:
                pass
            if os.path.isfile(default.field4):
                info['ssh_key'] = default.field4
    else:
        info['username'] = asset.username
        info['password'] = CRYPTOR.decrypt(asset.password)
    try:
        info['port'] = int(asset.port)
    except TypeError:
        info['port'] = int(default.field2)

    return info


def get_role_key(user, role):
    """
    由于role的key的权限是所有人可以读的， ansible执行命令等要求为600，所以拷贝一份到特殊目录
    :param user:
    :param role:
    :return: self key path
    """
    user_role_key_dir = os.path.join(KEY_DIR, 'user')
    user_role_key_path = os.path.join(user_role_key_dir, '%s_%s.pem' % (user.username, role.name))
    mkdir(user_role_key_dir, mode=777)
    if not os.path.isfile(user_role_key_path):
        with open(os.path.join(role.key_path, 'id_rsa')) as fk:
            with open(user_role_key_path, 'w') as fu:
                fu.write(fk.read())
        logger.debug(u"创建新的系统用户key %s, Owner: %s" % (user_role_key_path, user.username))
        chown(user_role_key_path, user.username)
        os.chmod(user_role_key_path, 0600)
    return user_role_key_path


def chown(path, user, group=''):
    if not group:
        group = user
    try:
        uid = pwd.getpwnam(user).pw_uid
        gid = pwd.getpwnam(group).pw_gid
        os.chown(path, uid, gid)
    except KeyError:
        pass


def page_list_return(total, current=1):
    """
    page
    分页，返回本次分页的最小页数到最大页数列表
    """
    min_page = current - 2 if current - 4 > 0 else 1
    max_page = min_page + 4 if min_page + 4 < total else total

    return range(min_page, max_page + 1)


def pages(post_objects, request):
    """
    page public function , return page's object tuple
    分页公用函数，返回分页的对象元组
    """
    paginator = Paginator(post_objects, 20)
    try:
        current_page = int(request.GET.get('page', '1'))
    except ValueError:
        current_page = 1

    page_range = page_list_return(len(paginator.page_range), current_page)

    try:
        page_objects = paginator.page(current_page)
    except (EmptyPage, InvalidPage):
        page_objects = paginator.page(paginator.num_pages)

    if current_page >= 5:
        show_first = 1
    else:
        show_first = 0

    if current_page <= (len(paginator.page_range) - 3):
        show_end = 1
    else:
        show_end = 0

    # 所有对象， 分页器， 本页对象， 所有页码， 本页页码，是否显示第一页，是否显示最后一页
    return post_objects, paginator, page_objects, page_range, current_page, show_first, show_end


class PyCrypt(object):
    """
    This class used to encrypt and decrypt password.
    加密类
    """

    def __init__(self, key):
        self.key = key
        self.mode = AES.MODE_CBC

    @staticmethod
    def gen_rand_pass(length=16, especial=False):
        """
        random password
        随机生成密码
        """
        salt_key = '1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_'
        symbol = '!@$%^&*()_'
        salt_list = []
        if especial:
            for i in range(length - 4):
                salt_list.append(random.choice(salt_key))
            for i in range(4):
                salt_list.append(random.choice(symbol))
        else:
            for i in range(length):
                salt_list.append(random.choice(salt_key))
        salt = ''.join(salt_list)
        return salt

    @staticmethod
    def md5_crypt(string):
        """
        md5 encrypt method
        md5非对称加密方法
        """
        return hashlib.new("md5", string).hexdigest()

    @staticmethod
    def gen_sha512(salt, password):
        """
        generate sha512 format password
        生成sha512加密密码
        """
        return crypt.crypt(password, '$6$%s$' % salt)

    def encrypt(self, passwd=None, length=32):
        """
        encrypt gen password
        对称加密之加密生成密码
        """
        if not passwd:
            passwd = self.gen_rand_pass()

        cryptor = AES.new(self.key, self.mode, b'8122ca7d906ad5e1')
        try:
            count = len(passwd)
        except TypeError:
            raise ServerError('Encrypt password error, TYpe error.')

        add = (length - (count % length))
        passwd += ('\0' * add)
        cipher_text = cryptor.encrypt(passwd)
        return b2a_hex(cipher_text)

    def decrypt(self, text):
        """
        decrypt pass base the same key
        对称加密之解密，同一个加密随机数
        """
        cryptor = AES.new(self.key, self.mode, b'8122ca7d906ad5e1')
        try:
            plain_text = cryptor.decrypt(a2b_hex(text))
        except TypeError:
            raise ServerError('Decrypt password error, TYpe error.')
        return plain_text.rstrip('\0')


class ServerError(Exception):
    """
    self define exception
    自定义异常
    """
    pass


def get_object(model, **kwargs):
    """
    use this function for query
    使用改封装函数查询数据库
    """
    for value in kwargs.values():
        if not value:
            return None

    the_object = model.objects.filter(**kwargs)
    if len(the_object) == 1:
        the_object = the_object[0]
    else:
        the_object = None
    return the_object


def require_role(role='user'):
    """
    decorator for require user role in ["super", "admin", "user"]
    要求用户是某种角色 ["super", "admin", "user"]的装饰器
    """

    def _deco(func):
        def __deco(request, *args, **kwargs):
            request.session['pre_url'] = request.path
            if not request.user.is_authenticated():
                return HttpResponseRedirect(reverse('login'))
            if role == 'admin':
                # if request.session.get('role_id', 0) < 1:
                if request.user.role == 'CU':
                    return HttpResponseRedirect(reverse('index'))
            elif role == 'super':
                # if request.session.get('role_id', 0) < 2:
                if request.user.role in ['CU', 'GA']:
                    return HttpResponseRedirect(reverse('index'))
            return func(request, *args, **kwargs)

        return __deco

    return _deco


def is_role_request(request, role='user'):
    """
    require this request of user is right
    要求请求角色正确
    """
    role_all = {'user': 'CU', 'admin': 'GA', 'super': 'SU'}
    if request.user.role == role_all.get(role, 'CU'):
        return True
    else:
        return False


def get_session_user_dept(request):
    """
    get department of the user in session
    获取session中用户的部门
    """
    # user_id = request.session.get('user_id', 0)
    # print '#' * 20
    # print user_id
    # user = User.objects.filter(id=user_id)
    # if user:
    #     user = user[0]
    #     return user, None
    return request.user, None


@require_role
def get_session_user_info(request):
    """
    get the user info of the user in session, for example id, username etc.
    获取用户的信息
    """
    # user_id = request.session.get('user_id', 0)
    # user = get_object(User, id=user_id)
    # if user:
    #     return [user.id, user.username, user]
    return [request.user.id, request.user.username, request.user]


def get_user_dept(request):
    """
    get the user dept id
    获取用户的部门id
    """
    user_id = request.user.id
    if user_id:
        user_dept = User.objects.get(id=user_id).dept
        return user_dept.id


def api_user(request):
    hosts = Log.objects.filter(is_finished=0).count()
    users = Log.objects.filter(is_finished=0).values('user').distinct().count()
    ret = {'users': users, 'hosts': hosts}
    json_data = json.dumps(ret)
    return HttpResponse(json_data)


def view_splitter(request, su=None, adm=None):
    """
    for different user use different view
    视图分页器
    """
    if is_role_request(request, 'super'):
        return su(request)
    elif is_role_request(request, 'admin'):
        return adm(request)
    else:
        return HttpResponseRedirect(reverse('login'))


def validate(request, user_group=None, user=None, asset_group=None, asset=None, edept=None):
    """
    validate the user request
    判定用户请求是否合法
    """
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
    """
    run a bash shell command
    执行bash命令
    """
    return subprocess.call(cmd, shell=True)


def mkdir(dir_name, username='', mode=755):
    """
    insure the dir exist and mode ok
    目录存在，如果不存在就建立，并且权限正确
    """
    cmd = '[ ! -d %s ] && mkdir -p %s && chmod %s %s' % (dir_name, dir_name, mode, dir_name)
    bash(cmd)
    if username:
        chown(dir_name, username)


def http_success(request, msg):
    return render_to_response('success.html', locals())


def http_error(request, emg):
    message = emg
    return render_to_response('error.html', locals())


def my_render(template, data, request):
    return render_to_response(template, data, context_instance=RequestContext(request))


def get_tmp_dir():
    seed = uuid.uuid4().hex[:4]
    dir_name = os.path.join('/tmp', '%s-%s' % (datetime.datetime.now().strftime('%Y%m%d-%H%M%S'), seed))
    mkdir(dir_name, mode=777)
    return dir_name


def defend_attack(func):
    def _deco(request, *args, **kwargs):
        if int(request.session.get('visit', 1)) > 10:
            logger.debug('请求次数: %s' % request.session.get('visit', 1))
            return HttpResponse('Forbidden', status=403)
        request.session['visit'] = request.session.get('visit', 1) + 1
        request.session.set_expiry(300)
        return func(request, *args, **kwargs)
    return _deco


def get_mac_address():
    node = uuid.getnode()
    mac = uuid.UUID(int=node).hex[-12:]
    return mac


CRYPTOR = PyCrypt(KEY)
logger = set_log(LOG_LEVEL)
