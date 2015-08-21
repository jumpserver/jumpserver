# coding: utf-8

import os, sys, time
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
import paramiko
import struct, fcntl, signal,socket, select, fnmatch
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.http import HttpResponse, Http404
from django.shortcuts import render_to_response
from juser.models import User, UserGroup, DEPT
from jasset.models import Asset, BisGroup, IDC
from jlog.models import Log
from jasset.models import AssetAlias
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect
from django.core.mail import send_mail
import json
import logging

try:
    import termios
    import tty
except ImportError:
    print '\033[1;31m仅支持类Unix系统 Only unix like supported.\033[0m'
    time.sleep(3)
    sys.exit()


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
log_dir = os.path.join(BASE_DIR, 'logs')

def set_log(level):
    log_level_total = {'debug': logging.DEBUG, 'info': logging.INFO, 'warning': logging.WARN, 'error': logging.ERROR,
                       'critical': logging.CRITICAL}
    logger = logging.getLogger('jumpserver')
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(JLOG_FILE)
    fh.setLevel(log_level_total.get(level, logging.DEBUG))
    formatter = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger


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


class Jtty(object):
    def __init__(self, user, asset):
        self.chan = None
        self.username = user.username
        self.ip = asset.ip
        self.user = user
        self.asset = asset

    @staticmethod
    def get_win_size():
        """
        This function use to get the size of the windows!
        获得terminal窗口大小
        """
        if 'TIOCGWINSZ' in dir(termios):
            TIOCGWINSZ = termios.TIOCGWINSZ
        else:
            TIOCGWINSZ = 1074295912L
        s = struct.pack('HHHH', 0, 0, 0, 0)
        x = fcntl.ioctl(sys.stdout.fileno(), TIOCGWINSZ, s)
        return struct.unpack('HHHH', x)[0:2]

    def set_win_size(self, sig, data):
        """
        This function use to set the window size of the terminal!
        设置terminal窗口大小
        """
        try:
            win_size = self.get_win_size()
            self.chan.resize_pty(height=win_size[0], width=win_size[1])
        except Exception:
            pass

    def log_record(self):
        """
        Logging user command and output.
        记录用户的日志
        """
        tty_log_dir = os.path.join(log_dir, 'tty')
        timestamp_start = int(time.time())
        date_start = time.strftime('%Y%m%d', time.localtime(timestamp_start))
        time_start = time.strftime('%H%M%S', time.localtime(timestamp_start))
        log_filename = '%s_%s_%s.log' % (self.username, self.ip, time_start)
        today_connect_log_dir = os.path.join(tty_log_dir, date_start)
        log_file_path = os.path.join(today_connect_log_dir, log_filename)
        dept_name = self.user.dept.name

        pid = os.getpid()
        pts = os.popen("ps axu | grep %s | grep -v grep | awk '{ print $7 }'" % pid).read().strip()
        ip_list = os.popen("who | grep %s | awk '{ print $5 }'" % pts).read().strip('()\n')

        try:
            is_dir(today_connect_log_dir)
        except OSError:
            raise ServerError('Create %s failed, Please modify %s permission.' % (today_connect_log_dir, tty_log_dir))

        try:
            log_file = open(log_file_path, 'a')
        except IOError:
            raise ServerError('Create logfile failed, Please modify %s permission.' % today_connect_log_dir)

        log = Log(user=self.username, host=self.ip, remote_ip=ip_list, dept_name=dept_name,
                  log_path=log_file_path, start_time=datetime.datetime.now(), pid=pid)
        log_file.write('Start time is %s\n' % datetime.datetime.now())
        log.save()
        return log_file, log

    def posix_shell(self):
        """
        Use paramiko channel connect server interactive.
        使用paramiko模块的channel，连接后端，进入交互式
        """
        log_file, log = self.log_record()
        old_tty = termios.tcgetattr(sys.stdin)
        try:
            tty.setraw(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
            self.chan.settimeout(0.0)

            while True:
                try:
                    r, w, e = select.select([self.chan, sys.stdin], [], [])
                except Exception:
                    pass

                if self.chan in r:
                    try:
                        x = self.chan.recv(1024)
                        if len(x) == 0:
                            break
                        sys.stdout.write(x)
                        sys.stdout.flush()
                        log_file.write(x)
                        log_file.flush()
                    except socket.timeout:
                        pass

                if sys.stdin in r:
                    x = os.read(sys.stdin.fileno(), 1)
                    if len(x) == 0:
                        break
                    self.chan.send(x)

        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
            log_file.write('End time is %s' % datetime.datetime.now())
            log_file.close()
            log.is_finished = True
            log.handle_finished = False
            log.end_time = datetime.datetime.now()
            log.save()

    def get_connect_item(self):
        """获取连接需要的参数，也就是服务ip, 端口, 用户账号和密码"""
        if not self.asset.is_active:
            raise ServerError('该主机被禁用 Host %s is not active.' % self.ip)

        if not self.user.is_active:
            raise ServerError('该用户被禁用 User %s is not active.' % self.username)

        login_type_dict = {
            'L': self.user.ldap_pwd,
        }

        if self.asset.login_type in login_type_dict:
            password = CRYPTOR.decrypt(login_type_dict[self.asset.login_type])
            return self.username, password, self.ip, int(self.asset.port)

        elif self.asset.login_type == 'M':
            username = self.asset.username
            password = CRYPTOR.decrypt(self.asset.password)
            return username, password, self.ip, int(self.asset.port)

        else:
            raise ServerError('不支持的服务器登录方式 Login type is not in ["L", "M"]')

    def connect(self):
        """
        Connect server.
        连接服务器
        """
        username, password, ip, port = self.get_connect_item()
        logger.debug("username: %s, password: %s, ip: %s, port: %s" % (username, password, ip, port))
        ps1 = "PS1='[\u@%s \W]\$ '\n" % self.ip
        login_msg = "clear;echo -e '\\033[32mLogin %s done. Enjoy it.\\033[0m'\n" % ip

        # 发起ssh连接请求 Make a ssh connection
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(ip, port=port, username=username, password=password, compress=True)
        except paramiko.ssh_exception.AuthenticationException, paramiko.ssh_exception.SSHException:
            raise ServerError('认证错误 Authentication Error.')
        except socket.error:
            raise ServerError('端口可能不对 Connect SSH Socket Port Error, Please Correct it.')

        # 获取连接的隧道并设置窗口大小 Make a channel and set windows size
        global channel
        win_size = self.get_win_size()
        self.chan = channel = ssh.invoke_shell(height=win_size[0], width=win_size[1])
        try:
            signal.signal(signal.SIGWINCH, self.set_win_size)
        except:
            pass

        # 设置PS1并提示 Set PS1 and msg it
        channel.send(ps1)
        channel.send(login_msg)

        # Make ssh interactive tunnel
        self.posix_shell()

        # Shutdown channel socket
        channel.close()
        ssh.close()


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
        the_object = None
    return the_object


def require_role(role='user'):
    """
    要求用户是某种角色 ["super", "admin", "user"]
    """
    def _deco(func):
        def __deco(request, *args, **kwargs):
            if role == 'user':
                if not request.session.get('user_id'):
                    return HttpResponseRedirect('/login/')
            elif role == 'admin':
                if request.session.get('role_id', 0) != 1:
                    return HttpResponseRedirect('/')
            elif role == 'super':
                if request.session.get('role_id', 0) != 2:
                    return HttpResponseRedirect('/')
            return func(request, *args, **kwargs)
        return __deco()
    return _deco


def is_role_request(request, role='user'):
    """
    :param request: 请求
    :param role: 角色
    :return: bool
    要求请求角色正确
    """
    role_all = {'user': 0, 'admin': 1, 'super': 2}
    if request.session.get('role_id') == role_all.get(role, '0'):
        return True
    else:
        return False


@require_role
def get_session_user_dept(request):
    user_id = request.session.get('user_id', 0)
    user = User.objects.filter(id=user_id)
    if user:
        user = user[0]
        dept = user.dept
        return user, dept


@require_role
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
    """目录存在，如果不存在就建立，并且权限正确"""
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

log_level = CONF.get('base', 'log')
logger = set_log(log_level)