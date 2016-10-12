#!/usr/bin/env python
# coding: utf-8

import sys

reload(sys)
sys.setdefaultencoding('utf8')

import os
import re
import time
import datetime
import textwrap
import getpass
import readline
import django
import paramiko
import errno
import pyte
import operator
import struct, fcntl, signal, socket, select
from io import open as copen
import uuid

os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings'
if not django.get_version().startswith('1.6'):
    setup = django.setup()
from django.contrib.sessions.models import Session
from jumpserver.api import ServerError, User, Asset, PermRole, AssetGroup, get_object, mkdir, get_asset_info
from jumpserver.api import logger, Log, TtyLog, get_role_key, CRYPTOR, bash, get_tmp_dir
from jperm.perm_api import gen_resource, get_group_asset_perm, get_group_user_perm, user_have_perm, PermRole
from jumpserver.settings import LOG_DIR, NAV_SORT_BY
from jperm.ansible_api import MyRunner
# from jlog.log_api import escapeString
from jlog.models import ExecLog, FileLog
from jlog.views import TermLogRecorder

login_user = get_object(User, username=getpass.getuser())
try:
    remote_ip = os.environ.get('SSH_CLIENT').split()[0]
except (IndexError, AttributeError):
    remote_ip = os.popen("who -m | awk '{ print $NF }'").read().strip('()\n')

try:
    import termios
    import tty
except ImportError:
    print '\033[1;31m仅支持类Unix系统 Only unix like supported.\033[0m'
    time.sleep(3)
    sys.exit()


def color_print(msg, color='red', exits=False):
    """
    Print colorful string.
    颜色打印字符或者退出
    """
    color_msg = {'blue': '\033[1;36m%s\033[0m',
                 'green': '\033[1;32m%s\033[0m',
                 'yellow': '\033[1;33m%s\033[0m',
                 'red': '\033[1;31m%s\033[0m',
                 'title': '\033[30;42m%s\033[0m',
                 'info': '\033[32m%s\033[0m'}
    msg = color_msg.get(color, 'red') % msg
    print msg
    if exits:
        time.sleep(2)
        sys.exit()
    return msg


def write_log(f, msg):
    msg = re.sub(r'[\r\n]', '\r\n', msg)
    f.write(msg)
    f.flush()


class Tty(object):
    """
    A virtual tty class
    一个虚拟终端类，实现连接ssh和记录日志，基类
    """
    def __init__(self, user, asset, role, login_type='ssh'):
        self.username = user.username
        self.asset_name = asset.hostname
        self.ip = None
        self.port = 22
        self.ssh = None
        self.channel = None
        self.asset = asset
        self.user = user
        self.role = role
        self.remote_ip = ''
        self.login_type = login_type
        self.vim_flag = False
        self.vim_end_pattern = re.compile(r'\x1b\[\?1049', re.X)
        self.vim_data = ''
        self.stream = None
        self.screen = None
        self.__init_screen_stream()

    def __init_screen_stream(self):
        """
        初始化虚拟屏幕和字符流
        """
        self.stream = pyte.ByteStream()
        self.screen = pyte.Screen(80, 24)
        self.stream.attach(self.screen)

    @staticmethod
    def is_output(strings):
        newline_char = ['\n', '\r', '\r\n']
        for char in newline_char:
            if char in strings:
                return True
        return False

    @staticmethod
    def command_parser(command):
        """
        处理命令中如果有ps1或者mysql的特殊情况,极端情况下会有ps1和mysql
        :param command:要处理的字符传
        :return:返回去除PS1或者mysql字符串的结果
        """
        result = None
        match = re.compile('\[?.*@.*\]?[\$#]\s').split(command)
        if match:
            # 只需要最后的一个PS1后面的字符串
            result = match[-1].strip()
        else:
            # PS1没找到,查找mysql
            match = re.split('mysql>\s', command)
            if match:
                # 只需要最后一个mysql后面的字符串
                result = match[-1].strip()
        return result

    def deal_command(self, data):
        """
        处理截获的命令
        :param data: 要处理的命令
        :return:返回最后的处理结果
        """
        command = ''
        try:
            self.stream.feed(data)
            # 从虚拟屏幕中获取处理后的数据
            for line in reversed(self.screen.buffer):
                line_data = "".join(map(operator.attrgetter("data"), line)).strip()
                if len(line_data) > 0:
                    parser_result = self.command_parser(line_data)
                    if parser_result is not None:
                        # 2个条件写一起会有错误的数据
                        if len(parser_result) > 0:
                            command = parser_result
                    else:
                        command = line_data
                    break
        except Exception:
            pass
        # 虚拟屏幕清空
        self.screen.reset()
        return command

    def get_log(self):
        """
        Logging user command and output.
        记录用户的日志
        """
        tty_log_dir = os.path.join(LOG_DIR, 'tty')
        date_today = datetime.datetime.now()
        date_start = date_today.strftime('%Y%m%d')
        time_start = date_today.strftime('%H%M%S')
        today_connect_log_dir = os.path.join(tty_log_dir, date_start)
        log_file_path = os.path.join(today_connect_log_dir, '%s_%s_%s' % (self.username, self.asset_name, time_start))

        try:
            mkdir(os.path.dirname(today_connect_log_dir), mode=777)
            mkdir(today_connect_log_dir, mode=777)
        except OSError:
            logger.debug('创建目录 %s 失败，请修改%s目录权限' % (today_connect_log_dir, tty_log_dir))
            raise ServerError('创建目录 %s 失败，请修改%s目录权限' % (today_connect_log_dir, tty_log_dir))

        try:
            log_file_f = open(log_file_path + '.log', 'a')
            log_time_f = open(log_file_path + '.time', 'a')
        except IOError:
            logger.debug('创建tty日志文件失败, 请修改目录%s权限' % today_connect_log_dir)
            raise ServerError('创建tty日志文件失败, 请修改目录%s权限' % today_connect_log_dir)

        if self.login_type == 'ssh':  # 如果是ssh连接过来，记录connect.py的pid，web terminal记录为日志的id
            pid = os.getpid()
            self.remote_ip = remote_ip  # 获取远端IP
        else:
            pid = 0

        log = Log(user=self.username, host=self.asset_name, remote_ip=self.remote_ip, login_type=self.login_type,
                  log_path=log_file_path, start_time=date_today, pid=pid)
        log.save()
        if self.login_type == 'web':
            log.pid = log.id  # 设置log id为websocket的id, 然后kill时干掉websocket
            log.save()

        log_file_f.write('Start at %s\r\n' % datetime.datetime.now())
        return log_file_f, log_time_f, log

    def get_connect_info(self):
        """
        获取需要登陆的主机的信息和映射用户的账号密码
        """
        asset_info = get_asset_info(self.asset)
        role_key = get_role_key(self.user, self.role)  # 获取角色的key，因为ansible需要权限是600，所以统一生成用户_角色key
        role_pass = CRYPTOR.decrypt(self.role.password)
        connect_info = {'user': self.user, 'asset': self.asset, 'ip': asset_info.get('ip'),
                        'port': int(asset_info.get('port')), 'role_name': self.role.name,
                        'role_pass': role_pass, 'role_key': role_key}
        logger.debug(connect_info)
        return connect_info

    def get_connection(self):
        """
        获取连接成功后的ssh
        """
        connect_info = self.get_connect_info()

        # 发起ssh连接请求 Make a ssh connection
        ssh = paramiko.SSHClient()
        # ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            role_key = connect_info.get('role_key')
            if role_key and os.path.isfile(role_key):
                try:
                    ssh.connect(connect_info.get('ip'),
                                port=connect_info.get('port'),
                                username=connect_info.get('role_name'),
                                password=connect_info.get('role_pass'),
                                key_filename=role_key,
                                look_for_keys=False)
                    return ssh
                except (paramiko.ssh_exception.AuthenticationException, paramiko.ssh_exception.SSHException):
                    logger.warning(u'使用ssh key %s 失败, 尝试只使用密码' % role_key)
                    pass

            ssh.connect(connect_info.get('ip'),
                        port=connect_info.get('port'),
                        username=connect_info.get('role_name'),
                        password=connect_info.get('role_pass'),
                        allow_agent=False,
                        look_for_keys=False)

        except (paramiko.ssh_exception.AuthenticationException, paramiko.ssh_exception.SSHException):
            raise ServerError('认证失败 Authentication Error.')
        except socket.error:
            raise ServerError('端口可能不对 Connect SSH Socket Port Error, Please Correct it.')
        else:
            self.ssh = ssh
            return ssh


class SshTty(Tty):
    """
    A virtual tty class
    一个虚拟终端类，实现连接ssh和记录日志
    """

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
            self.channel.resize_pty(height=win_size[0], width=win_size[1])
        except Exception:
            pass

    def posix_shell(self):
        """
        Use paramiko channel connect server interactive.
        使用paramiko模块的channel，连接后端，进入交互式
        """
        log_file_f, log_time_f, log = self.get_log()
        termlog = TermLogRecorder(User.objects.get(id=self.user.id))
        termlog.setid(log.id)
        old_tty = termios.tcgetattr(sys.stdin)
        pre_timestamp = time.time()
        data = ''
        input_mode = False
        try:
            tty.setraw(sys.stdin.fileno())
            tty.setcbreak(sys.stdin.fileno())
            self.channel.settimeout(0.0)

            while True:
                try:
                    r, w, e = select.select([self.channel, sys.stdin], [], [])
                    flag = fcntl.fcntl(sys.stdin, fcntl.F_GETFL, 0)
                    fcntl.fcntl(sys.stdin.fileno(), fcntl.F_SETFL, flag|os.O_NONBLOCK)
                except Exception:
                    pass

                if self.channel in r:
                    try:
                        x = self.channel.recv(10240)
                        if len(x) == 0:
                            break

                        index = 0
                        len_x = len(x)
                        while index < len_x:
                            try:
                                n = os.write(sys.stdout.fileno(), x[index:])
                                sys.stdout.flush()
                                index += n
                            except OSError as msg:
                                if msg.errno == errno.EAGAIN:
                                    continue
                        now_timestamp = time.time()
                        termlog.write(x)
                        termlog.recoder = False
                        log_time_f.write('%s %s\n' % (round(now_timestamp-pre_timestamp, 4), len(x)))
                        log_time_f.flush()
                        log_file_f.write(x)
                        log_file_f.flush()
                        pre_timestamp = now_timestamp
                        log_file_f.flush()

                        self.vim_data += x
                        if input_mode:
                            data += x

                    except socket.timeout:
                        pass

                if sys.stdin in r:
                    try:
                        x = os.read(sys.stdin.fileno(), 4096)
                    except OSError:
                        pass
                    termlog.recoder = True
                    input_mode = True
                    if self.is_output(str(x)):
                        # 如果len(str(x)) > 1 说明是复制输入的
                        if len(str(x)) > 1:
                            data = x
                        match = self.vim_end_pattern.findall(self.vim_data)
                        if match:
                            if self.vim_flag or len(match) == 2:
                                self.vim_flag = False
                            else:
                                self.vim_flag = True
                        elif not self.vim_flag:
                            self.vim_flag = False
                            data = self.deal_command(data)[0:200]
                            if data is not None:
                                TtyLog(log=log, datetime=datetime.datetime.now(), cmd=data).save()
                        data = ''
                        self.vim_data = ''
                        input_mode = False

                    if len(x) == 0:
                        break
                    self.channel.send(x)

        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
            log_file_f.write('End time is %s' % datetime.datetime.now())
            log_file_f.close()
            log_time_f.close()
            termlog.save()
            log.filename = termlog.filename
            log.is_finished = True
            log.end_time = datetime.datetime.now()
            log.save()

    def connect(self):
        """
        Connect server.
        连接服务器
        """
        # 发起ssh连接请求 Make a ssh connection
        ssh = self.get_connection()

        transport = ssh.get_transport()
        transport.set_keepalive(30)
        transport.use_compression(True)

        # 获取连接的隧道并设置窗口大小 Make a channel and set windows size
        global channel
        win_size = self.get_win_size()
        # self.channel = channel = ssh.invoke_shell(height=win_size[0], width=win_size[1], term='xterm')
        self.channel = channel = transport.open_session()
        channel.get_pty(term='xterm', height=win_size[0], width=win_size[1])
        channel.invoke_shell()
        try:
            signal.signal(signal.SIGWINCH, self.set_win_size)
        except:
            pass

        self.posix_shell()

        # Shutdown channel socket
        channel.close()
        ssh.close()


class Nav(object):
    """
    导航提示类
    """
    def __init__(self, user):
        self.user = user
        self.user_perm = get_group_user_perm(self.user)
        if NAV_SORT_BY == 'ip':
            self.perm_assets = sorted(self.user_perm.get('asset', []).keys(),
                                      key=lambda x: [int(num) for num in x.ip.split('.') if num.isdigit()])
        elif NAV_SORT_BY == 'hostname':
            self.perm_assets = self.natural_sort_hostname(self.user_perm.get('asset', []).keys())
        else:
            self.perm_assets = tuple(self.user_perm.get('asset', []))
        self.search_result = self.perm_assets
        self.perm_asset_groups = self.user_perm.get('asset_group', [])

    def natural_sort_hostname(self, list):
        convert = lambda text: int(text) if text.isdigit() else text.lower()
        alphanum_key = lambda x: [ convert(c) for c in re.split('([0-9]+)', x.hostname) ]
        return sorted(list, key = alphanum_key)

    @staticmethod
    def print_nav():
        """
        Print prompt
        打印提示导航
        """
        msg = """\n\033[1;32m###    欢迎使用Jumpserver开源跳板机系统   ### \033[0m

        1) 输入 \033[32mID\033[0m 直接登录 或 输入\033[32m部分 IP,主机名,备注\033[0m 进行搜索登录(如果唯一).
        2) 输入 \033[32m/\033[0m + \033[32mIP, 主机名 or 备注 \033[0m搜索. 如: /ip
        3) 输入 \033[32mP/p\033[0m 显示您有权限的主机.
        4) 输入 \033[32mG/g\033[0m 显示您有权限的主机组.
        5) 输入 \033[32mG/g\033[0m\033[0m + \033[32m组ID\033[0m 显示该组下主机. 如: g1
        6) 输入 \033[32mE/e\033[0m 批量执行命令.
        7) 输入 \033[32mU/u\033[0m 批量上传文件.
        8) 输入 \033[32mD/d\033[0m 批量下载文件.
        9) 输入 \033[32mH/h\033[0m 帮助.
        0) 输入 \033[32mQ/q\033[0m 退出.
        """
        print textwrap.dedent(msg)

    def get_asset_group_member(self, str_r):
        gid_pattern = re.compile(r'^g\d+$')

        if gid_pattern.match(str_r):
            gid = int(str_r.lstrip('g'))
            # 获取资产组包含的资产
            asset_group = get_object(AssetGroup, id=gid)
            if asset_group and asset_group in self.perm_asset_groups:
                self.search_result = list(asset_group.asset_set.all())
            else:
                color_print('没有该资产组或没有权限')
                return

    def search(self, str_r=''):
        # 搜索结果保存
        if str_r:
            try:
                id_ = int(str_r)
                if id_ < len(self.search_result):
                    self.search_result = [self.search_result[id_]]
                    return
                else:
                    raise ValueError

            except (ValueError, TypeError):
                # 匹配 ip, hostname, 备注
                str_r = str_r.lower()
                self.search_result = [asset for asset in self.perm_assets if str_r == str(asset.ip).lower()] or \
                                     [asset for asset in self.perm_assets if str_r in str(asset.ip).lower() \
                                      or str_r in str(asset.hostname).lower() \
                                      or str_r in str(asset.comment).lower()]
        else:
            # 如果没有输入就展现所有
            self.search_result = self.perm_assets

    @staticmethod
    def truncate_str(str_, length=30):
        str_ = str_.decode('utf-8')
        if len(str_) > length:
            return str_[:14] + '..' + str_[-14:]
        else:
            return str_

    @staticmethod
    def get_max_asset_property_length(assets, property_='hostname'):
        try:
            return max([len(getattr(asset, property_)) for asset in assets])
        except ValueError:
            return 30

    def print_search_result(self):
        hostname_max_length = self.get_max_asset_property_length(self.search_result)
        line = '[%-3s] %-16s %-5s  %-' + str(hostname_max_length) + 's %-10s %s'
        color_print(line % ('ID', 'IP', 'Port', 'Hostname', 'SysUser', 'Comment'), 'title')
        if hasattr(self.search_result, '__iter__'):
            for index, asset in enumerate(self.search_result):
                # 获取该资产信息
                asset_info = get_asset_info(asset)
                # 获取该资产包含的角色
                role = [str(role.name) for role in self.user_perm.get('asset').get(asset).get('role')]
                print line % (index, asset.ip, asset_info.get('port'),
                              self.truncate_str(asset.hostname), str(role).replace("'", ''), asset.comment)
        print

    def try_connect(self):
        try:
            asset = self.search_result[0]
            roles = list(self.user_perm.get('asset').get(asset).get('role'))
            if len(roles) == 1:
                role = roles[0]
            elif len(roles) > 1:
                print "\033[32m[ID] 系统用户\033[0m"
                for index, role in enumerate(roles):
                    print "[%-2s] %s" % (index, role.name)
                print
                print "授权系统用户超过1个，请输入ID, q退出"
                try:
                    role_index = raw_input("\033[1;32mID>:\033[0m ").strip()
                    if role_index == 'q':
                        return
                    else:
                        role = roles[int(role_index)]
                except IndexError:
                    color_print('请输入正确ID', 'red')
                    return
            else:
                color_print('没有映射用户', 'red')
                return

            print('Connecting %s ...' % asset.hostname)
            ssh_tty = SshTty(login_user, asset, role)
            ssh_tty.connect()
        except (KeyError, ValueError):
            color_print('请输入正确ID', 'red')
        except ServerError, e:
            color_print(e, 'red')

    def print_asset_group(self):
        """
        打印用户授权的资产组
        """
        user_asset_group_all = get_group_user_perm(self.user).get('asset_group', [])
        color_print('[%-3s] %-20s %s' % ('ID', '组名', '备注'), 'title')
        for asset_group in user_asset_group_all:
            print '[%-3s] %-15s %s' % (asset_group.id, asset_group.name, asset_group.comment)
        print

    def exec_cmd(self):
        """
        批量执行命令
        """
        while True:
            roles = self.user_perm.get('role').keys()
            if len(roles) > 1:  # 授权角色数大于1
                color_print('[%-2s] %-15s' % ('ID', '系统用户'),  'info')
                role_check = dict(zip(range(len(roles)), roles))

                for i, r in role_check.items():
                    print '[%-2s] %-15s' % (i, r.name)
                print
                print "请输入运行命令所关联系统用户的ID, q退出"

                try:
                    role_id = int(raw_input("\033[1;32mRole>:\033[0m ").strip())
                    if role_id == 'q':
                        break
                except (IndexError, ValueError):
                    color_print('错误输入')
                else:
                    role = role_check[int(role_id)]
            elif len(roles) == 1:  # 授权角色数为1
                role = roles[0]
            else:
                color_print('当前用户未被授予角色，无法执行任何操作，如有疑问请联系管理员。')
                return
            assets = list(self.user_perm.get('role', {}).get(role).get('asset'))  # 获取该用户，角色授权主机
            print "授权包含该系统用户的所有主机"
            for asset in assets:
                print ' %s' % asset.hostname
            print
            print "请输入主机名或ansible支持的pattern, 多个主机:分隔, q退出"
            pattern = raw_input("\033[1;32mPattern>:\033[0m ").strip()
            if pattern == 'q':
                break
            else:
                res = gen_resource({'user': self.user, 'asset': assets, 'role': role}, perm=self.user_perm)
                runner = MyRunner(res)
                asset_name_str = ''
                print "匹配主机:"
                for inv in runner.inventory.get_hosts(pattern=pattern):
                    print ' %s' % inv.name
                    asset_name_str += '%s ' % inv.name
                print

                while True:
                    print "请输入执行的命令， 按q退出"
                    command = raw_input("\033[1;32mCmds>:\033[0m ").strip()
                    if command == 'q':
                        break
                    elif not command:
                        color_print('命令不能为空...')
                        continue
                    runner.run('shell', command, pattern=pattern)
                    ExecLog(host=asset_name_str, user=self.user.username, cmd=command, remote_ip=remote_ip,
                            result=runner.results).save()
                    for k, v in runner.results.items():
                        if k == 'ok':
                            for host, output in v.items():
                                color_print("%s => %s" % (host, 'Ok'), 'green')
                                print output
                                print
                        else:
                            for host, output in v.items():
                                color_print("%s => %s" % (host, k), 'red')
                                color_print(output, 'red')
                                print
                    print "~o~ Task finished ~o~"
                    print

    def upload(self):
        while True:
            try:
                print "进入批量上传模式"
                print "请输入主机名或ansible支持的pattern, 多个主机:分隔 q退出"
                pattern = raw_input("\033[1;32mPattern>:\033[0m ").strip()
                if pattern == 'q':
                    break
                else:
                    assets = self.user_perm.get('asset').keys()
                    res = gen_resource({'user': self.user, 'asset': assets}, perm=self.user_perm)
                    runner = MyRunner(res)
                    asset_name_str = ''
                    print "匹配主机:"
                    for inv in runner.inventory.get_hosts(pattern=pattern):
                        print inv.name
                        asset_name_str += '%s ' % inv.name

                    if not asset_name_str:
                        color_print('没有匹配主机')
                        continue
                    tmp_dir = get_tmp_dir()
                    logger.debug('Upload tmp dir: %s' % tmp_dir)
                    os.chdir(tmp_dir)
                    bash('rz')
                    filename_str = ' '.join(os.listdir(tmp_dir))
                    if not filename_str:
                        color_print("上传文件为空")
                        continue
                    logger.debug('上传文件: %s' % filename_str)

                    runner = MyRunner(res)
                    runner.run('copy', module_args='src=%s dest=%s directory_mode'
                                                     % (tmp_dir, '/tmp'), pattern=pattern)
                    ret = runner.results
                    FileLog(user=self.user.name, host=asset_name_str, filename=filename_str,
                            remote_ip=remote_ip, type='upload', result=ret).save()
                    logger.debug('Upload file: %s' % ret)
                    if ret.get('failed'):
                        error = '上传目录: %s \n上传失败: [ %s ] \n上传成功 [ %s ]' % (tmp_dir,
                                                                             ', '.join(ret.get('failed').keys()),
                                                                             ', '.join(ret.get('ok').keys()))
                        color_print(error)
                    else:
                        msg = '上传目录: %s \n传送成功 [ %s ]' % (tmp_dir, ', '.join(ret.get('ok').keys()))
                        color_print(msg, 'green')
                    print

            except IndexError:
                pass

    def download(self):
        while True:
            try:
                print "进入批量下载模式"
                print "请输入主机名或ansible支持的pattern, 多个主机:分隔,q退出"
                pattern = raw_input("\033[1;32mPattern>:\033[0m ").strip()
                if pattern == 'q':
                    break
                else:
                    assets = self.user_perm.get('asset').keys()
                    res = gen_resource({'user': self.user, 'asset': assets}, perm=self.user_perm)
                    runner = MyRunner(res)
                    asset_name_str = ''
                    print "匹配主机:\n"
                    for inv in runner.inventory.get_hosts(pattern=pattern):
                        asset_name_str += '%s ' % inv.name
                        print ' %s' % inv.name
                    if not asset_name_str:
                        color_print('没有匹配主机')
                        continue
                    print
                    while True:
                        tmp_dir = get_tmp_dir()
                        logger.debug('Download tmp dir: %s' % tmp_dir)
                        print "请输入文件路径(不支持目录)"
                        file_path = raw_input("\033[1;32mPath>:\033[0m ").strip()
                        if file_path == 'q':
                            break

                        if not file_path:
                            color_print("文件路径为空")
                            continue

                        runner.run('fetch', module_args='src=%s dest=%s' % (file_path, tmp_dir), pattern=pattern)
                        ret = runner.results
                        FileLog(user=self.user.name, host=asset_name_str, filename=file_path, type='download',
                                remote_ip=remote_ip, result=ret).save()
                        logger.debug('Download file result: %s' % ret)
                        os.chdir('/tmp')
                        tmp_dir_name = os.path.basename(tmp_dir)
                        if not os.listdir(tmp_dir):
                            color_print('下载全部失败')
                            continue
                        bash('tar czf %s.tar.gz %s && sz %s.tar.gz' % (tmp_dir, tmp_dir_name, tmp_dir))

                        if ret.get('failed'):
                            error = '文件名称: %s \n下载失败: [ %s ] \n下载成功 [ %s ]' % \
                                    ('%s.tar.gz' % tmp_dir_name, ', '.join(ret.get('failed').keys()), ', '.join(ret.get('ok').keys()))
                            color_print(error)
                        else:
                            msg = '文件名称: %s \n下载成功 [ %s ]' % ('%s.tar.gz' % tmp_dir_name, ', '.join(ret.get('ok').keys()))
                            color_print(msg, 'green')
                        print
            except IndexError:
                pass


def main():
    """
    he he
    主程序
    """
    if not login_user:  # 判断用户是否存在
        color_print('没有该用户，或许你是以root运行的 No that user.', exits=True)

    if not login_user.is_active:
        color_print('您的用户已禁用，请联系管理员.', exits=True)

    gid_pattern = re.compile(r'^g\d+$')
    nav = Nav(login_user)
    nav.print_nav()

    try:
        while True:
            try:
                option = raw_input("\033[1;32mOpt or ID>:\033[0m ").strip()
            except EOFError:
                nav.print_nav()
                continue
            except KeyboardInterrupt:
                sys.exit(0)
            if option in ['P', 'p', '\n', '']:
                nav.search()
                nav.print_search_result()
                continue
            if option.startswith('/'):
                nav.search(option.lstrip('/'))
                nav.print_search_result()
            elif gid_pattern.match(option):
                nav.get_asset_group_member(str_r=option)
                nav.print_search_result()
            elif option in ['G', 'g']:
                nav.print_asset_group()
                continue
            elif option in ['E', 'e']:
                nav.exec_cmd()
                continue
            elif option in ['U', 'u']:
                nav.upload()
            elif option in ['D', 'd']:
                nav.download()
            elif option in ['H', 'h']:
                nav.print_nav()
            elif option in ['Q', 'q', 'exit']:
                sys.exit()
            else:
                nav.search(option)
                if len(nav.search_result) == 1:
                    print('Only match Host:  %s ' % nav.search_result[0].hostname)
                    nav.try_connect()
                else:
                    nav.print_search_result()

    except IndexError, e:
        color_print(e)
        time.sleep(5)

if __name__ == '__main__':
    main()
