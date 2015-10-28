# coding: utf-8

import os, sys, time
from ConfigParser import ConfigParser
import getpass
from Crypto.Cipher import AES
import crypt
from binascii import b2a_hex, a2b_hex
import hashlib
import datetime
import random
import subprocess
import paramiko
import struct, fcntl, signal,socket, select, fnmatch
import re

from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.http import HttpResponse, Http404
from django.template import RequestContext
from juser.models import User, UserGroup
from jasset.models import Asset, AssetGroup
from jasset.models import AssetAlias
from jlog.models import Log, TtyLog
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
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
# LDAP_ENABLE = CONF.getint('ldap', 'ldap_enable')
URL = CONF.get('base', 'url')
MAIL_ENABLE = CONF.get('mail', 'mail_enable')
MAIL_FROM = CONF.get('mail', 'email_host_user')
log_dir = os.path.join(BASE_DIR, 'logs')


def set_log(level):
    """
    return a log file object
    根据提示设置log打印
    """
    log_level_total = {'debug': logging.DEBUG, 'info': logging.INFO, 'warning': logging.WARN, 'error': logging.ERROR,
                       'critical': logging.CRITICAL}
    logger_f = logging.getLogger('jumpserver')
    logger_f.setLevel(logging.DEBUG)
    fh = logging.FileHandler(JLOG_FILE)
    fh.setLevel(log_level_total.get(level, logging.DEBUG))
    formatter = logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger_f.addHandler(fh)
    return logger_f


def page_list_return(total, current=1):
    """
    page
    分页，返回本次分页的最小页数到最大页数列表
    """
    min_page = current - 2 if current - 4 > 0 else 1
    max_page = min_page + 4 if min_page + 4 < total else total

    return range(min_page, max_page+1)


def pages(post_objects, request):
    """
    page public function , return page's object tuple
    分页公用函数，返回分页的对象元组
    """
    paginator = Paginator(post_objects, 10)
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


def remove_control_char(str_r):
    """
    处理日志特殊字符
    """
    control_char = re.compile(r"""
            \x1b[ #%()*+\-.\/]. |
            \r |                                               #匹配 回车符(CR)
            (?:\x1b\[|\x9b) [ -?]* [@-~] |                     #匹配 控制顺序描述符(CSI)... Cmd
            (?:\x1b\]|\x9d) .*? (?:\x1b\\|[\a\x9c]) | \x07 |   #匹配 操作系统指令(OSC)...终止符或振铃符(ST|BEL)
            (?:\x1b[P^_]|[\x90\x9e\x9f]) .*? (?:\x1b\\|\x9c) | #匹配 设备控制串或私讯或应用程序命令(DCS|PM|APC)...终止符(ST)
            \x1b.                                              #匹配 转义过后的字符
            [\x80-\x9f]                                        #匹配 所有控制字符
            """, re.X)
    backspace = re.compile(r"[^\b][\b]")
    line_filtered = control_char.sub('', str_r.rstrip())
    while backspace.search(line_filtered):
        line_filtered = backspace.sub('', line_filtered)

    return line_filtered


def newline_code_in(strings):
    for i in ['\r', '\r\n', '\n']:
        if i in strings:
            #print "new line"
            return True
    return False


class Jtty(object):
    """
    A virtual tty class
    一个虚拟终端类，实现连接ssh和记录日志
    """
    def __init__(self, username, ip):
        self.chan = None
        self.username = username
        self.ip = ip
        # self.user = user
        # self.asset = asset

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
        today_connect_log_dir = os.path.join(tty_log_dir, date_start)
        log_file_path = os.path.join(today_connect_log_dir, '%s_%s_%s' % (self.username, self.ip, time_start))
        pid = os.getpid()
        pts = os.popen("ps axu | grep %s | grep -v grep | awk '{ print $7 }'" % pid).read().strip()
        ip_list = os.popen("who | grep %s | awk '{ print $5 }'" % pts).read().strip('()\n')

        try:
            is_dir(today_connect_log_dir)
        except OSError:
            raise ServerError('Create %s failed, Please modify %s permission.' % (today_connect_log_dir, tty_log_dir))

        try:
            log_file_f = open(log_file_path + '.log', 'a')
            log_time_f = open(log_file_path + '.time', 'a')
        except IOError:
            raise ServerError('Create logfile failed, Please modify %s permission.' % today_connect_log_dir)

        log = Log(user=self.username, host=self.ip, remote_ip=ip_list,
                  log_path=log_file_path, start_time=datetime.datetime.now(), pid=pid)
        log_file_f.write('Start time is %s\n' % datetime.datetime.now())
        log.save()
        return log_file_f, log_time_f, ip_list, log

    def posix_shell(self):
        """
        Use paramiko channel connect server interactive.
        使用paramiko模块的channel，连接后端，进入交互式
        """
        log_file_f, log_time_f, ip_list, log = self.log_record()
        old_tty = termios.tcgetattr(sys.stdin)
        pre_timestamp = time.time()
        input_r = ''
        input_mode = False

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
                        log_file_f.write(x)
                        now_timestamp = time.time()
                        log_time_f.write('%s %s\n' % (round(now_timestamp-pre_timestamp, 4), len(x)))
                        pre_timestamp = now_timestamp
                        log_file_f.flush()
                        log_time_f.flush()

                        if input_mode and not newline_code_in(x):
                            input_r += x

                    except socket.timeout:
                        pass

                if sys.stdin in r:
                    x = os.read(sys.stdin.fileno(), 1)
                    if not input_mode:
                        input_mode = True

                    if str(x) in ['\r', '\n', '\r\n']:
                        input_r = remove_control_char(input_r)
                        TtyLog(log_id=log.id, username=self.username, host=self.ip, remote_ip=ip_list, datetime=datetime.datetime.now(), cmd=input_r).save()
                        input_r = ''
                        input_mode = False

                    if len(x) == 0:
                        break
                    self.chan.send(x)

        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
            log_file_f.write('End time is %s' % datetime.datetime.now())
            log_file_f.close()
            log.is_finished = True
            log.end_time = datetime.datetime.now()
            log.save()

    def get_connect_item(self):
        """
        get args for connect: ip, port, username, passwd
        获取连接需要的参数，也就是服务ip, 端口, 用户账号和密码
        """
        # if not self.asset.is_active:
        #     raise ServerError('该主机被禁用 Host %s is not active.' % self.ip)
        #
        # if not self.user.is_active:
        #     raise ServerError('该用户被禁用 User %s is not active.' % self.username)

        # password = CRYPTOR.decrypt(self.])
        # return self.username, password, self.ip, int(self.asset.port)
        return 'root', 'redhat', '127.0.0.1', 22

    def get_connection(self):
        """
        Get the ssh connection for reuse
        获取连接套接字
        """
        username, password, ip, port = self.get_connect_item()
        logger.debug("username: %s, password: %s, ip: %s, port: %s" % (username, password, ip, port))

        # 发起ssh连接请求 Make a ssh connection
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(ip, port=port, username=username, password=password)
        except paramiko.ssh_exception.AuthenticationException, paramiko.ssh_exception.SSHException:
            raise ServerError('认证错误 Authentication Error.')
        except socket.error:
            raise ServerError('端口可能不对 Connect SSH Socket Port Error, Please Correct it.')
        else:
            return ssh

    def connect(self):
        """
        Connect server.
        连接服务器
        """
        ps1 = "PS1='[\u@%s \W]\$ '\n" % self.ip
        login_msg = "clear;echo -e '\\033[32mLogin %s done. Enjoy it.\\033[0m'\n" % self.ip

        # 发起ssh连接请求 Make a ssh connection
        ssh = self.get_connection()

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

    def execute(self, cmd):
        """
        execute cmd on the asset
        执行命令
        """
        pass


class PyCrypt(object):
    """
    This class used to encrypt and decrypt password.
    加密类
    """

    def __init__(self, key):
        self.key = key
        self.mode = AES.MODE_CBC

    @staticmethod
    def random_pass(length, especial=False):
        """
        random password
        随机生成密码
        """
        salt_key = '1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_'
        symbol = '!@$%^&*()_'
        salt_list = []
        if especial:
            for i in range(length-4):
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
            passwd = self.random_pass()

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
            # raise ServerError('Decrypt password error, TYpe error.')
            pass
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
            if role == 'user':
                if not request.session.get('user_id'):
                    return HttpResponseRedirect('/login/')
            elif role == 'admin':
                if request.session.get('role_id', 0) < 1:
                    return HttpResponseRedirect('/')
            elif role == 'super':
                if request.session.get('role_id', 0) < 2:
                    return HttpResponseRedirect('/')
            return func(request, *args, **kwargs)
        return __deco
    return _deco


def is_role_request(request, role='user'):
    """
    require this request of user is right
    要求请求角色正确
    """
    role_all = {'user': 0, 'admin': 1, 'super': 2}
    if request.session.get('role_id') == role_all.get(role, 0):
        return True
    else:
        return False


def get_session_user_dept(request):
    """
    get department of the user in session
    获取session中用户的部门
    """
    user_id = request.session.get('user_id', 0)
    print '#' * 20
    print user_id
    user = User.objects.filter(id=user_id)
    if user:
        user = user[0]
        return user, None


@require_role
def get_session_user_info(request):
    """
    get the user info of the user in session, for example id, username etc.
    获取用户的信息
    """
    user_id = request.session.get('user_id', 0)
    user = get_object(User, id=user_id)
    if user:
        return [user.id, user.username, user]


def get_user_dept(request):
    """
    get the user dept id
    获取用户的部门id
    """
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
        return HttpResponseRedirect('/login/')


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


def is_dir(dir_name, username='root', mode=0755):
    """
    insure the dir exist and mode ok
    目录存在，如果不存在就建立，并且权限正确
    """
    if not os.path.isdir(dir_name):
        os.makedirs(dir_name)
        bash("chown %s:%s '%s'" % (username, username, dir_name))
    os.chmod(dir_name, mode)


def http_success(request, msg):
    return render_to_response('success.html', locals())


def http_error(request, emg):
    message = emg
    return render_to_response('error.html', locals())


def my_render(template, data, request):
    return render_to_response(template, data, context_instance=RequestContext(request))


CRYPTOR = PyCrypt(KEY)

log_level = CONF.get('base', 'log')
logger = set_log(log_level)