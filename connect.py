# coding: utf-8

import sys

reload(sys)
sys.setdefaultencoding('utf8')

import socket
import os
import re
import select
import time
import paramiko
import struct
import fcntl
import signal
import textwrap
import getpass
import fnmatch
import readline
import django
import datetime
from multiprocessing import Pool

os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings'
if django.get_version() != '1.6':
    django.setup()
from juser.models import User
from jlog.models import Log
from jumpserver.api import CONF, BASE_DIR, ServerError, Juser, JassetGroup
from jumpserver.api import AssetAlias, get_connect_item, logger

try:
    import termios
    import tty
except ImportError:
    print '\033[1;31mOnly unix like supported.\033[0m'
    time.sleep(3)
    sys.exit()

CONF.read(os.path.join(BASE_DIR, 'jumpserver.conf'))
log_dir = os.path.join(BASE_DIR, 'logs')
login_name = getpass.getuser()
user = Juser(username=login_name)


def color_print(msg, color='blue'):
    """
    Print colorful string.
    颜色打印
    """
    color_msg = {'blue': '\033[1;36m%s\033[0m',
                 'green': '\033[1;32m%s\033[0m',
                 'red': '\033[1;31m%s\033[0m'}

    print color_msg.get(color, 'blue') % msg


def color_print_exit(msg, color='red'):
    """
    Print colorful string and exit.
    颜色打印并推出
    """
    color_print(msg, color=color)
    time.sleep(2)
    sys.exit()


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


def set_win_size(sig, data):
    """
    This function use to set the window size of the terminal!
    设置terminal窗口大小
    """
    try:
        win_size = get_win_size()
        channel.resize_pty(height=win_size[0], width=win_size[1])
    except Exception:
        pass


def log_record(username, host):
    """
    Logging user command and output.
    记录用户的日志
    """
    connect_log_dir = os.path.join(log_dir, 'connect')
    timestamp_start = int(time.time())
    today = time.strftime('%Y%m%d', time.localtime(timestamp_start))
    time_now = time.strftime('%H%M%S', time.localtime(timestamp_start))
    today_connect_log_dir = os.path.join(connect_log_dir, today)
    log_filename = '%s_%s_%s.log' % (username, host, time_now)
    log_file_path = os.path.join(today_connect_log_dir, log_filename)
    dept = User.objects.filter(username=username)
    if dept:
        dept = dept[0]
        dept_name = dept.name
    else:
        dept_name = 'None'

    pid = os.getpid()
    pts = os.popen("ps axu | grep %s | grep -v grep | awk '{ print $7 }'" % pid).read().strip()
    remote_ip = os.popen("who | grep %s | awk '{ print $5 }'" % pts).read().strip('()\n')

    if not os.path.isdir(today_connect_log_dir):
        try:
            os.makedirs(today_connect_log_dir)
            os.chmod(today_connect_log_dir, 0777)
        except OSError:
            raise ServerError('Create %s failed, Please modify %s permission.' % (today_connect_log_dir, connect_log_dir))

    try:
        log_file = open(log_file_path, 'a')
    except IOError:
        raise ServerError('Create logfile failed, Please modify %s permission.' % today_connect_log_dir)

    log = Log(user=username, host=host, remote_ip=remote_ip, dept_name=dept_name,
              log_path=log_file_path, start_time=datetime.datetime.now(), pid=pid)
    log_file.write('Start time is %s\n' % datetime.datetime.now())
    log.save()
    return log_file, log


def posix_shell(chan, username, host):
    """
    Use paramiko channel connect server interactive.
    使用paramiko模块的channel，连接后端，进入交互式
    """
    log_file, log = log_record(username, host)
    old_tty = termios.tcgetattr(sys.stdin)
    try:
        tty.setraw(sys.stdin.fileno())
        tty.setcbreak(sys.stdin.fileno())
        chan.settimeout(0.0)

        while True:
            try:
                r, w, e = select.select([chan, sys.stdin], [], [])
            except Exception:
                pass

            if chan in r:
                try:
                    x = chan.recv(1024)
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
                chan.send(x)

    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
        log_file.write('End time is %s' % datetime.datetime.now())
        log_file.close()
        log.is_finished = True
        log.log_finished = False
        log.end_time = datetime.datetime.now()
        log.save()


# def get_user_host_group(username):
#     """
#     Get the host groups of under the user control.
#     获取用户有权限的主机组
#     """
#     groups_attr = {}
#     group_all = get_host_groups(username)
#     for group in group_all:
#         groups_attr[group.name] = [group.id, group.comment]
#     return groups_attr


# def get_user_host_group_member(username, gid):
#     """
#     Get the host group hosts of under the user control.
#     获取用户有权限主机组下的主机
#     """
#     groups_attr = get_user_host_group(username)
#     groups_ids = [attr[0] for name, attr in groups_attr.items()]
#     hosts_attr = {}
#     if int(gid) in groups_ids:
#         user = User.objects.filter(username=username)
#         if user:
#             user = user[0]
#             hosts = get_host_groups(gid)
#             for host in hosts:
#                 alias = AssetAlias.objects.filter(user=user, host=host)
#                 if alias and alias[0].alias != '':
#                     hosts_attr[host.ip] = [host.id, host.ip, alias[0].alias]
#                 else:
#                     hosts_attr[host.ip] = [host.id, host.ip, host.comment]
#     return hosts_attr


# def user_asset_info(user, printable=False):
#     """
#     Get or Print asset info
#     获取或打印用户资产信息
#     """
#     assets_info = {}
#     try:
#         assets = get_asset(user)
#     except ServerError, e:
#         color_print(e, 'red')
#         return
#
#     for asset in assets:
#         asset_alias = AssetAlias.objects.filter(user=user, asset=asset)
#         if asset_alias and asset_alias[0].alias != '':
#             assets_info[asset.ip] = [asset.id, asset.ip, asset_alias[0].alias]
#         else:
#             assets_info[asset.ip] = [asset.id, asset.ip, asset.comment]
#
#     if printable:
#         ips = assets_info.keys()
#         ips.sort()
#         for ip in ips:
#             print '%-15s -- %s' % (ip, assets_info[ip][2])
#         print ''
#     else:
#         return assets_info


def verify_connect(username, part_ip):
    pass
    # ip_matched = []
    # try:
    #     assets = get_asset(username=username)
    # except ServerError, e:
    #     color_print(e, 'red')
    #     return False
    #
    # assets_info =
    # for ip_info in hosts:
    #     if part_ip in ip_info[1:] and part_ip:
    #         ip_matched = [ip_info[1]]
    #         break
    #     for info in ip_info[1:]:
    #         if part_ip in info:
    #             ip_matched.append(ip_info[1])
    #
    # ip_matched = list(set(ip_matched))
    # if len(ip_matched) > 1:
    #     for ip in ip_matched:
    #         print '%-15s -- %s' % (ip, hosts_attr[ip][2])
    # elif len(ip_matched) < 1:
    #     color_print('No Permission or No host.', 'red')
    # else:
    #     username, password, host, port = get_connect_item(username, ip_matched[0])
    #     connect(username, password, host, port, login_name)


def print_prompt():
    msg = """\033[1;32m###  Welcome Use JumpServer To Login. ### \033[0m
    1) Type \033[32mIP or Part IP, Host Alias or Comments \033[0m To Login.
    2) Type \033[32mP/p\033[0m To Print The Servers You Available.
    3) Type \033[32mG/g\033[0m To Print The Server Groups You Available.
    4) Type \033[32mG/g(1-N)\033[0m To Print The Server Group Hosts You Available.
    5) Type \033[32mE/e\033[0m To Execute Command On Several Servers.
    6) Type \033[32mQ/q\033[0m To Quit.
    """
    print textwrap.dedent(msg)


# def print_user_host_group(username):
#     host_groups = get_host_groups(username)
#     for host_group in host_groups:
#         print "[%3s] %s -- %s" % (host_group.id, host_group.ip, host_group.comment)


# def asset_group_member(username, gid):
#     pattern = re.compile(r'\d+')
#     match = pattern.match(gid)
#
#     if match:
#         hosts_attr = get_host_group_host(username, gid)
#         hosts = hosts_attr.keys()
#         hosts.sort()
#         for ip in hosts:
#             print '%-15s -- %s' % (ip, hosts_attr[ip][2])
#     else:
#         color_print('No such group id, Please check it.', 'red')


def connect(username, password, host, port, login_name):
    """
    Connect server.
    """
    ps1 = "PS1='[\u@%s \W]\$ '\n" % host
    login_msg = "clear;echo -e '\\033[32mLogin %s done. Enjoy it.\\033[0m'\n" % host

    # Make a ssh connection
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(host, port=port, username=username, password=password, compress=True)
    except paramiko.ssh_exception.AuthenticationException, paramiko.ssh_exception.SSHException:
        raise ServerError('Authentication Error.')
    except socket.error:
        raise ServerError('Connect SSH Socket Port Error, Please Correct it.')

    # Make a channel and set windows size
    global channel
    win_size = get_win_size()
    channel = ssh.invoke_shell(height=win_size[0], width=win_size[1])
    try:
        signal.signal(signal.SIGWINCH, set_win_size)
    except:
        pass

    # Set PS1 and msg it
    channel.send(ps1)
    channel.send(login_msg)

    # Make ssh interactive tunnel
    posix_shell(channel, login_name, host)

    # Shutdown channel socket
    channel.close()
    ssh.close()


def remote_exec_cmd(ip, port, username, password, cmd):
    try:
        time.sleep(5)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(ip, port, username, password, timeout=5)
        stdin, stdout, stderr = ssh.exec_command("bash -l -c '%s'" % cmd)
        out = stdout.readlines()
        err = stderr.readlines()
        color_print('%s:' % ip, 'blue')
        for i in out:
            color_print(" " * 4 + i.strip(), 'green')
        for j in err:
            color_print(" " * 4 + j.strip(), 'red')
        ssh.close()
    except Exception as e:
        color_print(ip + ':', 'blue')
        color_print(str(e), 'red')


def multi_remote_exec_cmd(hosts, username, cmd):
    pool = Pool(processes=5)
    for host in hosts:
        username, password, ip, port = get_connect_item(username, host)
        pool.apply_async(remote_exec_cmd, (ip, port, username, password, cmd))
    pool.close()
    pool.join()


def exec_cmd_servers(username):
    color_print("You can choose in the following IP(s), Use glob or ips split by comma. q/Q to PreLayer.", 'green')
    user.get_asset_info(printable=True)
    while True:
        hosts = []
        inputs = raw_input('\033[1;32mip(s)>: \033[0m')
        if inputs in ['q', 'Q']:
            break
        get_hosts = user.get_asset_info().keys()

        if ',' in inputs:
            ips_input = inputs.split(',')
            for host in ips_input:
                if host in get_hosts:
                    hosts.append(host)
        else:
            for host in get_hosts:
                if fnmatch.fnmatch(host, inputs):
                    hosts.append(host.strip())

        if len(hosts) == 0:
            color_print("Check again, Not matched any ip!", 'red')
            continue
        else:
            print "You matched ip: %s" % hosts
        color_print("Input the Command , The command will be Execute on servers, q/Q to quit.", 'green')
        while True:
            cmd = raw_input('\033[1;32mCmd(s): \033[0m')
            if cmd in ['q', 'Q']:
                break
            exec_log_dir = os.path.join(log_dir, 'exec_cmds')
            if not os.path.isdir(exec_log_dir):
                os.mkdir(exec_log_dir)
                os.chmod(exec_log_dir, 0777)
            filename = "%s/%s.log" % (exec_log_dir, time.strftime('%Y%m%d'))
            f = open(filename, 'a')
            f.write("DateTime: %s User: %s Host: %s Cmds: %s\n" %
                    (time.strftime('%Y/%m/%d %H:%M:%S'), username, hosts, cmd))
            multi_remote_exec_cmd(hosts, username, cmd)


if __name__ == '__main__':
    if not user.validate():
        color_print_exit(u'没有该用户 No that user.')

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
                user.get_asset_info(printable=True)
                continue
            elif option in ['G', 'g']:
                user.get_asset_group_info(printable=True)
                continue
            elif gid_pattern.match(option):
                gid = option[1:].strip()
                asset_group = JassetGroup(id=gid)
                asset_group.get_asset_info(printable=True)
                continue
            elif option in ['E', 'e']:
                exec_cmd_servers(login_name)
            elif option in ['Q', 'q', 'exit']:
                sys.exit()
            else:
                try:
                    verify_connect(login_name, option)
                except ServerError, e:
                    color_print(e, 'red')
    except IndexError:
        pass
