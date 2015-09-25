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
import datetime
from multiprocessing import Pool

os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings'
from juser.models import User
from jlog.models import Log
from jumpserver.api import CONF, BASE_DIR, ServerError, user_perm_group_api, user_perm_group_hosts_api, get_user_host
from jumpserver.api import AssetAlias, get_connect_item


try:
    import termios
    import tty
except ImportError:
    print '\033[1;31mOnly UnixLike supported.\033[0m'
    time.sleep(3)
    sys.exit()

CONF.read(os.path.join(BASE_DIR, 'jumpserver.conf'))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
SSH_KEY_DIR = os.path.join(BASE_DIR, 'keys')
SERVER_KEY_DIR = os.path.join(SSH_KEY_DIR, 'server')
LOGIN_NAME = getpass.getuser()


def color_print(msg, color='blue'):
    """Print colorful string."""
    color_msg = {'blue': '\033[1;36m%s\033[0m',
                 'green': '\033[1;32m%s\033[0m',
                 'red': '\033[1;31m%s\033[0m'}

    print color_msg.get(color, 'blue') % msg


def color_print_exit(msg, color='red'):
    """Print colorful string and exit."""
    color_print(msg, color=color)
    time.sleep(2)
    sys.exit()


def get_win_size():
    """This function use to get the size of the windows!"""
    if 'TIOCGWINSZ' in dir(termios):
        TIOCGWINSZ = termios.TIOCGWINSZ
    else:
        TIOCGWINSZ = 1074295912L  # Assume
    s = struct.pack('HHHH', 0, 0, 0, 0)
    x = fcntl.ioctl(sys.stdout.fileno(), TIOCGWINSZ, s)
    return struct.unpack('HHHH', x)[0:2]


def set_win_size(sig, data):
    """This function use to set the window size of the terminal!"""
    try:
        win_size = get_win_size()
        channel.resize_pty(height=win_size[0], width=win_size[1])
    except:
        pass


def log_record(username, host):
    """Logging user command and output."""
    connect_log_dir = os.path.join(LOG_DIR, 'connect')
    timestamp_start = int(time.time())
    today = time.strftime('%Y%m%d', time.localtime(timestamp_start))
    time_now = time.strftime('%H%M%S', time.localtime(timestamp_start))
    today_connect_log_dir = os.path.join(connect_log_dir, today)
    log_filename = '%s_%s_%s.log' % (username, host, time_now)
    log_file_path = os.path.join(today_connect_log_dir, log_filename)
    dept_name = User.objects.get(username=username).dept.name
    pid = os.getpid()
    pts = os.popen("ps axu | awk '$2==%s{ print $7 }'" % pid).read().strip()
    ip_list = os.popen("who | awk '$2==\"%s\"{ print $5 }'" % pts).read().strip('()\n')

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

    log = Log(user=username, host=host, remote_ip=ip_list, dept_name=dept_name,
              log_path=log_file_path, start_time=datetime.datetime.now(), pid=pid)
    log_file.write('Starttime is %s\n' % datetime.datetime.now())
    log.save()
    return log_file, log


def posix_shell(chan, username, host):
    """
    Use paramiko channel connect server interactive.
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
            except:
                pass

            if chan in r:
                try:
                    x = chan.recv(10240)
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
        log_file.write('Endtime is %s' % datetime.datetime.now())
        log_file.close()
        log.is_finished = True
        log.log_finished = False
        log.end_time = datetime.datetime.now()
        log.save()
        print_prompt()


def get_user_hostgroup(username):
    """Get the hostgroups of under the user control."""
    groups_attr = {}
    group_all = user_perm_group_api(username)
    for group in group_all:
        groups_attr[group.name] = [group.id, group.comment]
    return groups_attr


def get_user_hostgroup_host(username, gid):
    """Get the hostgroup hosts of under the user control."""
    hosts_attr = {}
    user = User.objects.get(username=username)
    hosts = user_perm_group_hosts_api(gid)
    for host in hosts:
        alias = AssetAlias.objects.filter(user=user, host=host)
        if alias and alias[0].alias != '':
            hosts_attr[host.ip] = [host.id, host.ip, alias[0].alias]
        else:
            hosts_attr[host.ip] = [host.id, host.ip, host.comment]
    return hosts_attr


def verify_connect(username, part_ip):
    ip_matched = []
    try:
        hosts_attr = get_user_host(username)
        hosts = hosts_attr.values()
    except ServerError, e:
        color_print(e, 'red')
        return False

    for ip_info in hosts:
        if part_ip in ip_info[1:] and part_ip:
            ip_matched = [ip_info[1]]
            break
        for info in ip_info[1:]:
            if part_ip in info:
                ip_matched.append(ip_info[1])

    ip_matched = list(set(ip_matched))
    if len(ip_matched) > 1:
        for ip in ip_matched:
            print '%-15s -- %s' % (ip, hosts_attr[ip][2])
    elif len(ip_matched) < 1:
        color_print('No Permission or No host.', 'red')
    else:
        username, password, host, port = get_connect_item(username, ip_matched[0])
        connect(username, password, host, port, LOGIN_NAME)


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


def print_user_host(username):
    try:
        hosts_attr = get_user_host(username)
    except ServerError, e:
        color_print(e, 'red')
        return
    hosts = hosts_attr.keys()
    hosts.sort()
    for ip in hosts:
        print '%-15s -- %s' % (ip, hosts_attr[ip][2])
    print ''


def print_user_hostgroup(username):
    group_attr = get_user_hostgroup(username)
    groups = group_attr.keys()
    for g in groups:
        print "[%3s] %s -- %s" % (group_attr[g][0], g, group_attr[g][1])


def print_user_hostgroup_host(username, gid):
    pattern = re.compile(r'\d+')
    match = pattern.match(gid)
    if match:
        hosts_attr = get_user_hostgroup_host(username, gid)
        hosts = hosts_attr.keys()
        hosts.sort()
        for ip in hosts:
            print '%-15s -- %s' % (ip, hosts_attr[ip][2])
    else:
        color_print('No such group id, Please check it.', 'red')


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
    print_user_host(LOGIN_NAME)
    while True:
        hosts = []
        inputs = raw_input('\033[1;32mip(s)>: \033[0m')
        if inputs in ['q', 'Q']:
            break
        get_hosts = get_user_host(username).keys()

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
            exec_log_dir = os.path.join(LOG_DIR, 'exec_cmds')
            if not os.path.isdir(exec_log_dir):
                os.mkdir(exec_log_dir)
                os.chmod(exec_log_dir, 0777)
            filename = "%s/%s.log" % (exec_log_dir, time.strftime('%Y%m%d'))
            f = open(filename, 'a')
            f.write("DateTime: %s User: %s Host: %s Cmds: %s\n" %
                    (time.strftime('%Y/%m/%d %H:%M:%S'), username, hosts, cmd))
            multi_remote_exec_cmd(hosts, username, cmd)


if __name__ == '__main__':
    print_prompt()
    gid_pattern = re.compile(r'^g\d+$')
    try:
        while True:
            try:
                option = raw_input("\033[1;32mOpt or IP>:\033[0m ")
            except EOFError:
                print
                continue
            except KeyboardInterrupt:
                sys.exit(0)
            if option in ['P', 'p']:
                print_user_host(LOGIN_NAME)
                continue
            elif option in ['G', 'g']:
                print_user_hostgroup(LOGIN_NAME)
                continue
            elif gid_pattern.match(option):
                gid = option[1:].strip()
                print_user_hostgroup_host(LOGIN_NAME, gid)
                continue
            elif option in ['E', 'e']:
                exec_cmd_servers(LOGIN_NAME)
            elif option in ['Q', 'q', 'exit']:
                sys.exit()
            else:
                try:
                    verify_connect(LOGIN_NAME, option)
                except ServerError, e:
                    color_print(e, 'red')
    except IndexError:
        pass
