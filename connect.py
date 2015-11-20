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
import struct, fcntl, signal, socket, select

os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings'
if django.get_version() != '1.6':
    django.setup()
from jumpserver.api import ServerError, User, Asset, AssetGroup, get_object, mkdir
from jumpserver.api import logger, Log, TtyLog
from jumpserver.settings import LOG_DIR
from jperm.ansible_api import Command

login_user = get_object(User, username=getpass.getuser())
VIM_FLAG = False

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
                 'red': '\033[1;31m%s\033[0m'}

    print color_msg.get(color, 'blue') % msg
    if exits:
        time.sleep(2)
        sys.exit()


def check_vim_status(command, ssh):
    global SSH_TTY
    print command
    if command == '':
        return True
    else:
        command_str= 'ps -ef |grep "%s" | grep "%s"|grep -v grep |wc -l' % (command,SSH_TTY)
        print command_str
        stdin, stdout, stderr = ssh.exec_command(command_str)
        ps_num = stdout.read()
        print ps_num
        if int(ps_num) == 0:
            return True
        else:
            return False


class Tty(object):
    """
    A virtual tty class
    一个虚拟终端类，实现连接ssh和记录日志，基类
    """
    def __init__(self, username, asset_name):
        self.username = username
        self.asset_name = asset_name
        self.ip = None
        self.port = 22
        self.channel = None
        #self.asset = get_object(Asset, name=asset_name)
        #self.user = get_object(User, username=username)
        self.role = None
        self.ssh = None
        self.connect_info = None
        self.login_type = 'ssh'

    @staticmethod
    def is_output(strings):
        newline_char = ['\n', '\r', '\r\n']
        for char in newline_char:
            if char in strings:
                return True
        return False

    @staticmethod
    def deal_command(str_r, ssh):
        """
                处理命令中特殊字符
        """
        str_r = re.sub('\x07','',str_r)   #删除响铃
        patch_char = re.compile('\x08\x1b\[C')      #删除方向左右一起的按键
        while patch_char.search(str_r):
            str_r = patch_char.sub('', str_r.rstrip())

        result_command = ''      #最后的结果
        backspace_num = 0              #光标移动的个数
        backspace_list = []
        reach_backspace_flag = False    #没有检测到光标键则为true
        reach_backspace_second_flag = False
        pattern_list = []
        pattern_str=''
        while str_r:
            tmp = re.match(r'\s*\w+\s*', str_r)                 #获取字符串，其它特殊字符匹配暂时还不知道。。
            if tmp:
                if reach_backspace_flag :
                    if not reach_backspace_second_flag:
                        pattern_str +=str(tmp.group(0))
                    else:
                        pattern_list.append(pattern_str)
                        pattern_str=str(tmp.group(0))
                        reach_backspace_second_flag=False
                    str_r = str_r[len(str(tmp.group(0))):]
                    continue
                else:
                    result_command += str(tmp.group(0))
                    str_r = str_r[len(str(tmp.group(0))):]
                    continue

            tmp = re.match(r'\x1b\[K[\x08]*', str_r)           #遇到删除确认符，确定删除数据
            if tmp:
                for x in backspace_list:
                    backspace_num += int(x)
                if backspace_num > 0:
                    if backspace_num > len(result_command) :
                        result_command += ''.join(pattern_list)
                        result_command += pattern_str
                        result_command = result_command[0:-backspace_num]
                    else:
                        result_command = result_command[0:-backspace_num]
                        result_command += ''.join(pattern_list)
                        result_command += pattern_str
                del_len = len(str(tmp.group(0)))-3
                if del_len > 0:
                    result_command = result_command[0:-del_len]
                reach_backspace_flag = False
                reach_backspace_second_flag =False
                backspace_num =0
                del pattern_list[:]
                del backspace_list[:]
                pattern_str=''
                str_r = str_r[len(str(tmp.group(0))):]
                continue

            tmp = re.match(r'\x08+', str_r)                    #将遇到的退格数字存放到队列中
            if tmp:
                if reach_backspace_flag:
                    reach_backspace_second_flag = True
                else:
                    reach_backspace_flag = True
                str_r = str_r[len(str(tmp.group(0))):]
                if len(str_r) != 0:                             #如果退格键在最后，则放弃
                    backspace_list.append(len(str(tmp.group(0))))
                continue

            if reach_backspace_flag :
                if not reach_backspace_second_flag:
                    pattern_str +=str_r[0]
                else:
                    pattern_list.append(pattern_str)
                    pattern_str=str_r[0]
                    reach_backspace_second_flag=False
            else :
                result_command += str_r[0]
            str_r = str_r[1:]

        if pattern_str !='':
            pattern_list.append(pattern_str)

        #退格队列中还有腿哥键，则进行删除操作
        if len(backspace_list) > 0 :
                for backspace in backspace_list:
                    if int(backspace) >= len(result_command):
                        result_command = pattern_list[0]
                    else:
                        result_command = result_command[:-int(backspace)]
                        result_command += pattern_list[0]
                    pattern_list = pattern_list[1:]

        control_char = re.compile(r"""
                \x1b[ #%()*+\-.\/]. |
                \r |                                               #匹配 回车符(CR)
                (?:\x1b\[|\x9b) [ -?]* [@-~] |                     #匹配 控制顺序描述符(CSI)... Cmd
                (?:\x1b\]|\x9d) .*? (?:\x1b\\|[\a\x9c]) | \x07 |   #匹配 操作系统指令(OSC)...终止符或振铃符(ST|BEL)
                (?:\x1b[P^_]|[\x90\x9e\x9f]) .*? (?:\x1b\\|\x9c) | #匹配 设备控制串或私讯或应用程序命令(DCS|PM|APC)...终止符(ST)
                \x1b.                                              #匹配 转义过后的字符
                [\x80-\x9f] | (?:\x1b\]0.*) | \[.*@.*\][\$#] | (.*mysql>.*)      #匹配 所有控制字符
                """, re.X)
        result_command = control_char.sub('', result_command.strip())
        global VIM_FLAG
        global VIM_COMMAND
        if not VIM_FLAG:
            if result_command.startswith('vi'):
                VIM_FLAG = True
                VIM_COMMAND = result_command
            return result_command.decode('utf8',"ignore")
        else:
            if check_vim_status(VIM_COMMAND, ssh):
                VIM_FLAG = False
                VIM_COMMAND=''
                if result_command.endswith(':wq') or result_command.endswith(':wq!') or result_command.endswith(':q!'):
                    return ''
                return result_command.decode('utf8',"ignore")
            else:
                return ''

    @staticmethod
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
            mkdir(os.path.dirname(today_connect_log_dir), mode=0777)
            mkdir(today_connect_log_dir, mode=0777)
        except OSError:
            logger.debug('创建目录 %s 失败，请修改%s目录权限' % (today_connect_log_dir, tty_log_dir))
            raise ServerError('Create %s failed, Please modify %s permission.' % (today_connect_log_dir, tty_log_dir))

        try:
            log_file_f = open(log_file_path + '.log', 'a')
            log_time_f = open(log_file_path + '.time', 'a')
        except IOError:
            logger.debug('创建tty日志文件失败, 请修改目录%s权限' % today_connect_log_dir)
            raise ServerError('Create logfile failed, Please modify %s permission.' % today_connect_log_dir)

        if self.login_type == 'ssh':  # 如果是ssh连接过来，记录connect.py的pid，web terminal记录为日志的id
            pid = os.getpid()
            remote_ip = os.popen("who -m | awk '{ print $5 }'").read().strip('()\n')  # 获取远端IP
            log = Log(user=self.username, host=self.asset_name, remote_ip=remote_ip,
                      log_path=log_file_path, start_time=date_today, pid=pid)
        else:
            remote_ip = 'Web'
            log = Log(user=self.username, host=self.asset_name, remote_ip=remote_ip,
                      log_path=log_file_path, start_time=date_today, pid=0)
            log.save()
            log.pid = log.id

        log.save()
        log_file_f.write('Start at %s\n' % datetime.datetime.now())
        return log_file_f, log_time_f, log

    def get_connect_info(self):
        """
        获取需要登陆的主机的信息和映射用户的账号密码
        """

        # 1. get ip, port
        # 2. get 映射用户
        # 3. get 映射用户的账号，密码或者key
        # self.connect_info = {'user': '', 'asset': '', 'ip': '', 'port': 0, 'role_name': '', 'role_pass': '', 'role_key': ''}
        self.connect_info = {'user': 'a', 'asset': 'b', 'ip': '127.0.0.1', 'port': 22, 'role_name': 'root', 'role_pass': 'redhat', 'role_key': ''}
        return self.connect_info

    def get_connection(self):
        """
        获取连接成功后的ssh
        """
        connect_info = self.get_connect_info()

        # 发起ssh连接请求 Make a ssh connection
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            role_key = connect_info.get('role_key')
            if role_key and os.path.isfile(role_key):
                try:
                    ssh.connect(connect_info.get('ip'),
                                port=connect_info.get('port'),
                                username=connect_info.get('role_name'),
                                key_filename=role_key,
                                look_for_keys=False)
                    self.ssh = ssh
                    return ssh
                except paramiko.ssh_exception.AuthenticationException, paramiko.ssh_exception.SSHException:
                    pass

            ssh.connect(connect_info.get('ip'),
                        port=connect_info.get('port'),
                        username=connect_info.get('role_name'),
                        password=connect_info.get('role_pass'),
                        look_for_keys=False)

        except paramiko.ssh_exception.AuthenticationException, paramiko.ssh_exception.SSHException:
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
                except Exception:
                    pass

                if self.channel in r:
                    try:
                        x = self.channel.recv(1024)
                        if len(x) == 0:
                            break
                        sys.stdout.write(x)
                        sys.stdout.flush()
                        now_timestamp = time.time()
                        log_time_f.write('%s %s\n' % (round(now_timestamp-pre_timestamp, 4), len(x)))
                        log_file_f.write(x)
                        pre_timestamp = now_timestamp
                        log_file_f.flush()
                        log_time_f.flush()

                        if input_mode and not self.is_output(x):
                            data += x

                    except socket.timeout:
                        pass

                if sys.stdin in r:
                    x = os.read(sys.stdin.fileno(), 1)
                    input_mode = True

                    if str(x) in ['\r', '\n', '\r\n']:
                        data = self.deal_command(data, self.ssh)

                        TtyLog(log=log, datetime=datetime.datetime.now(), cmd=data).save()
                        data = ''
                        input_mode = False

                    if len(x) == 0:
                        break
                    self.channel.send(x)

        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
            log_file_f.write('End time is %s' % datetime.datetime.now())
            log_file_f.close()
            log.is_finished = True
            log.end_time = datetime.datetime.now()
            log.save()

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
        self.channel = channel = ssh.invoke_shell(height=win_size[0], width=win_size[1], term='xterm')
        try:
            signal.signal(signal.SIGWINCH, self.set_win_size)
        except:
            pass

        # 设置PS1并提示 Set PS1 and msg it
        #channel.send(ps1)
        #channel.send(login_msg)
        # channel.send('echo ${SSH_TTY}\n')
        # global SSH_TTY
        # while not channel.recv_ready():
        #     time.sleep(1)
        # tmp = channel.recv(1024)
        #print 'ok'+tmp+'ok'
        # SSH_TTY  = re.search(r'(?<=/dev/).*', tmp).group().strip()
        # SSH_TTY = ''
        # channel.send('clear\n')
        # Make ssh interactive tunnel
        self.posix_shell()

        # Shutdown channel socket
        channel.close()
        ssh.close()


class Nav(object):
    def __init__(self, user):
        self.user = user
        self.search_result = {}

    @staticmethod
    def print_nav():
        """
        Print prompt
        打印提示导航
        """
        msg = """\n\033[1;32m###  Welcome To Use JumpServer, A Open Source System . ### \033[0m
        1) Type \033[32mID\033[0m To Login.
        2) Type \033[32m/\033[0m + \033[32mIP, Host Name, Host Alias or Comments \033[0mTo Search.
        3) Type \033[32mP/p\033[0m To Print The Servers You Available.
        4) Type \033[32mG/g\033[0m To Print The Server Groups You Available.
        5) Type \033[32mG/g\033[0m\033[0m + \033[32mGroup ID\033[0m To Print The Server Group You Available.
        6) Type \033[32mE/e\033[0m To Execute Command On Several Servers.
        7) Type \033[32mQ/q\033[0m To Quit.
        """

        msg = """\n\033[1;32m###  欢迎使用Jumpserver开源跳板机  ### \033[0m
        1) 输入 \033[32mID\033[0m 直接登录.
        2) 输入 \033[32m/\033[0m + \033[32mIP, 主机名, 主机别名 or 备注 \033[0m搜索.
        3) 输入 \033[32mP/p\033[0m 显示您有权限的主机.
        4) 输入 \033[32mG/g\033[0m 显示您有权限的主机组.
        5) 输入 \033[32mG/g\033[0m\033[0m + \033[32m组ID\033[0m 显示该组下主机.
        6) 输入 \033[32mE/e\033[0m 批量执行命令.
        7) 输入 \033[32mQ/q\033[0m 退出.
        """
        print textwrap.dedent(msg)

    def search(self, str_r=''):
        gid_pattern = re.compile(r'^g\d+$')
        user_asset_all = list(Asset.objects.all())
        user_asset_search = []
        if str_r:
            if gid_pattern.match(str_r):
                user_asset_search = list(Asset.objects.all())
            else:
                for asset in user_asset_all:
                    if str_r in asset.ip or str_r in str(asset.comment):
                        user_asset_search.append(asset)
        else:
            user_asset_search = user_asset_all

        self.search_result = dict(zip(range(len(user_asset_search)), user_asset_search))

        print '\033[32m[%-3s] %-15s  %-15s  %-5s  %-5s  %s \033[0m' % ('ID', 'AssetName', 'IP', 'Port', 'Role', 'Comment')
        for index, asset in self.search_result.items():
            if asset.comment:
                print '[%-3s] %-15s  %-15s  %-5s  %-5s  %s' % (index, 'asset_name'+str(index), asset.ip, asset.port, 'role', asset.comment)
            else:
                print '[%-3s] %-15s  %-15s  %-5s  %-5s' % (index, 'asset_name'+str(index), asset.ip, asset.port, 'role')
        print

    @staticmethod
    def print_asset_group():
        user_asset_group_all = AssetGroup.objects.all()

        print '\033[32m[%-3s] %-15s %s \033[0m' % ('ID', 'GroupName', 'Comment')
        for asset_group in user_asset_group_all:
            if asset_group.comment:
                print '[%-3s] %-15s %s' % (asset_group.id, asset_group.name, asset_group.comment)
            else:
                print '[%-3s] %-15s' % (asset_group.id, asset_group.name)
        print

    def exec_cmd(self):
        self.search()
        while True:
            print "请输入主机名、IP或ansile支持的pattern, q退出"
            try:
                pattern = raw_input("\033[1;32mPattern>:\033[0m ").strip()
                if pattern == 'q':
                    break
                else:
                    res = {
                            "group1": {
                                "hosts": [{"hostname": "127.0.0.1", "port": "22", "username": "lastimac", "password": "redhat"}, {"hostname": "192.168.244.129", "port": "22", "username": "root", "password": "redhat"}, {"hostname": "j", "port": "22", "username": "root", "password": "redhat"}],
                                "vars": {"var1": 'a', "var2": 'a'}
                            }
                        }
                    cmd = Command(res)
                    for inv in cmd.inventory.get_hosts(pattern=pattern):
                        print inv.name
                    confirm_host = raw_input("\033[1;32mIs that [y/n]>:\033[0m ").strip()
                    if confirm_host == 'y':
                        while True:
                            print "请输入执行的命令， 按q退出"
                            command = raw_input("\033[1;32mCmds>:\033[0m ").strip()
                            if command == 'q':
                                break
                            result = cmd.run(module_name='shell', command=command, pattern=pattern)
                            for k, v in result.items():
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
                                print "=" * 20
                                print
                    else:
                        continue

            except EOFError:
                print
                break


def main():
    """
    he he
    主程序
    """
    if not login_user:  # 判断用户是否存在
        color_print(u'没有该用户，或许你是以root运行的 No that user.', exits=True)

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
                continue
            if option.startswith('/') or gid_pattern.match(option):
                nav.search(option.lstrip('/'))
            elif option in ['G', 'g']:
                nav.print_asset_group()
                continue
            elif option in ['E', 'e']:
                nav.exec_cmd()
                continue
            elif option in ['Q', 'q', 'exit']:
                sys.exit()
            else:
                try:
                    asset = nav.search_result[int(option)]
                    ssh_tty = SshTty('a', 'b')
                    ssh_tty.connect()
                except (KeyError, ValueError):
                    color_print('请输入正确ID', 'red')
                except ServerError, e:
                    color_print(e, 'red')
    except IndexError:
        pass

if __name__ == '__main__':
    main()


