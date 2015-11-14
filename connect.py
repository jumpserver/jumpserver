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
from multiprocessing import Pool
import paramiko
import struct, fcntl, signal, socket, select, fnmatch

os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings'
if django.get_version() != '1.6':
    django.setup()
from jumpserver.api import ServerError, User, Asset, AssetGroup, get_object
from jumpserver.api import logger, is_dir, Log, TtyLog
from jumpserver.settings import log_dir

try:
    import termios
    import tty
except ImportError:
    print '\033[1;31m仅支持类Unix系统 Only unix like supported.\033[0m'
    time.sleep(3)
    sys.exit()

VIM_FLAG = False
VIM_COMMAND = ''
SSH_TTY = ''
login_user = get_object(User, username=getpass.getuser())


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


def verify_connect(user, option):
    """
    Check user was permed or not . Check ip is unique or not.
    鉴定用户是否有该主机权限 或 匹配到的ip是否唯一
    """
    ip_matched = []
    try:
        assets_info = login_user.get_asset_info()
    except ServerError, e:
        color_print(e, 'red')
        return False

    for ip, asset_info in assets_info.items():
        if option in asset_info[1:] and option:
            ip_matched = [asset_info[1]]
            break

        for info in asset_info[1:]:
            if option in info:
                ip_matched.append(ip)

    logger.debug('%s matched input %s: %s' % (login_user.username, option, ip_matched))
    ip_matched = list(set(ip_matched))

    if len(ip_matched) > 1:  # 如果匹配ip不唯一
        ip_comment = {}
        for ip in ip_matched:
            ip_comment[ip] = assets_info[ip][2]

        for ip in sorted(ip_comment):
            if ip_comment[ip]:
                print '%-15s -- %s' % (ip, ip_comment[ip])
            else:
                print '%-15s' % ip
        print ''
    elif len(ip_matched) < 1:  # 如果没匹配到
        color_print('没有该主机，或者您没有该主机的权限 No Permission or No host.', 'red')
    else:  # 恰好是1个
        asset = get_object(Asset, ip=ip_matched[0])
        jtty = Jtty(user, asset)
        jtty.connect()


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


def deal_command(str_r, ssh):
    
    """
            处理命令中特殊字符
    """
    t = time.time()
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


def newline_code_in(strings):
    for i in ['\r', '\r\n', '\n']:
        if i in strings:
            #print "new line"
            return True
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
        self.user = None
        self.asset = None
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

    def get_log_file(self):
        """
        Logging user command and output.
        记录用户的日志
        """
        tty_log_dir = os.path.join(log_dir, 'tty')
        timestamp_start = int(time.time())
        date_start = time.strftime('%Y%m%d', time.localtime(timestamp_start))
        time_start = time.strftime('%H%M%S', time.localtime(timestamp_start))
        today_connect_log_dir = os.path.join(tty_log_dir, date_start)
        log_file_path = os.path.join(today_connect_log_dir, '%s_%s_%s' % (self.username, self.asset_name, time_start))

        try:
            is_dir(today_connect_log_dir, mode=0777)
        except OSError:
            raise ServerError('Create %s failed, Please modify %s permission.' % (today_connect_log_dir, tty_log_dir))

        try:
            log_file_f = open(log_file_path + '.log', 'a')
            log_time_f = open(log_file_path + '.time', 'a')
        except IOError:
            raise ServerError('Create logfile failed, Please modify %s permission.' % today_connect_log_dir)

        if self.login_type == 'ssh':
            pid = os.getpid()
            remote_ip = os.popen("who -m | awk '{ print $5 }'").read().strip('()\n')
            log = Log(user=self.username, host=self.asset_name, remote_ip=remote_ip,
                      log_path=log_file_path, start_time=datetime.datetime.now(), pid=pid)
        else:
            remote_ip = 'Web'
            log = Log(user=self.username, host=self.asset_name, remote_ip=remote_ip,
                      log_path=log_file_path, start_time=datetime.datetime.now(), pid=0)
            log.save()
            log.pid = log.id
            log.save()

        log_file_f.write('Start at %s\n' % datetime.datetime.now())
        log.save()
        return log_file_f, log_time_f, log

    def get_connect_info(self):
        """
        获取需要登陆的主机的信息和映射用户的账号密码
        """

        # 1. get ip, port
        # 2. get 映射用户
        # 3. get 映射用户的账号，密码或者key
        # self.connect_info = {'user': '', 'asset': '', 'ip': '', 'port': 0, 'role_name': '', 'role_pass': '', 'role_key': ''}
        self.connect_info = {'user': 'a', 'asset': 'b', 'ip': '127.0.0.1', 'port': 22, 'role_name': 'root', 'role_pass': '', 'role_key': '/root/.ssh/id_rsa.bak'}
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
            if connect_info.get('role_pass'):
                ssh.connect(connect_info.get('ip'),
                            port=connect_info.get('port'),
                            username=connect_info.get('role_name'),
                            password=connect_info.get('role_pass'),
                            look_for_keys=False)
            else:
                ssh.connect(connect_info.get('ip'),
                            port=connect_info.get('port'),
                            username=connect_info.get('role_name'),
                            key_filename=connect_info.get('role_key'),
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
        log_file_f, log_time_f, log = self.get_log_file()
        old_tty = termios.tcgetattr(sys.stdin)
        pre_timestamp = time.time()
        input_r = ''
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
                            input_r += x

                    except socket.timeout:
                        pass

                if sys.stdin in r:
                    x = os.read(sys.stdin.fileno(), 1)
                    if not input_mode:
                        input_mode = True

                    if str(x) in ['\r', '\n', '\r\n']:
                        # input_r = deal_command(input_r,ssh)
                        input_r = self.remove_control_char(input_r)

                        TtyLog(log=log, datetime=datetime.datetime.now(), cmd=input_r).save()
                        input_r = ''
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
        channel.send('clear\n')
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


def print_prompt():
    """
    Print prompt
    打印提示导航
    """
    msg = """\033[1;32m###  Welcome Use JumpServer To Login. ### \033[0m
    1) Type \033[32mIP or Part IP, Host Alias or Comments \033[0m To Login.
    2) Type \033[32mP/p\033[0m To Print The Servers You Available.
    3) Type \033[32mG/g\033[0m To Print The Server Groups You Available.
    4) Type \033[32mG/g(1-N)\033[0m To Print The Server Group Hosts You Available.
    5) Type \033[32mE/e\033[0m To Execute Command On Several Servers.
    6) Type \033[32mQ/q\033[0m To Quit.
    """
    print textwrap.dedent(msg)


def main():
    """
    he he
    主程序
    """
    if not login_user:  # 判断用户是否存在
        color_print(u'没有该用户，或许你是以root运行的 No that user.', exits=True)

    print_prompt()
    gid_pattern = re.compile(r'^g\d+$')

    try:
        while True:
            try:
                option = raw_input("\033[1;32mOpt or IP>:\033[0m ")
            except EOFError:
                print_prompt()
                continue
            except KeyboardInterrupt:
                sys.exit(0)
            if option in ['P', 'p']:
                login_user.get_asset_info(printable=True)
                continue
            elif option in ['G', 'g']:
                login_user.get_asset_group_info(printable=True)
                continue
            elif gid_pattern.match(option):
                gid = option[1:].strip()
                asset_group = get_object(AssetGroup, id=gid)
                if asset_group and asset_group.is_permed(user=login_user):
                    asset_group.get_asset_info(printable=True)
                continue
            elif option in ['E', 'e']:
                # exec_cmd_servers(login_name)
                pass
            elif option in ['Q', 'q', 'exit']:
                sys.exit()
            else:
                try:
                    verify_connect(login_user, option)
                except ServerError, e:
                    color_print(e, 'red')
    except IndexError:
        pass

if __name__ == '__main__':
    main()


