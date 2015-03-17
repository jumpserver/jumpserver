# coding: utf-8

import socket
import sys
import os
import ast
import select
import time
from datetime import datetime
import paramiko
import struct
import fcntl
import signal
import textwrap
import django
import getpass
import fnmatch
import readline
from multiprocessing import Pool
from ConfigParser import ConfigParser
from django.core.exceptions import ObjectDoesNotExist

os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings'
django.setup()
from juser.models import User
from jasset.models import Asset
from jlog.models import Log
from jumpserver.views import PyCrypt
from jumpserver.api import user_perm_asset_api, user_perm_group_api

try:
    import termios
    import tty
except ImportError:
    print '\033[1;31mOnly postfix supported.\033[0m'
    time.sleep(3)
    sys.exit()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
CONF = ConfigParser()
CONF.read(os.path.join(BASE_DIR, 'jumpserver.conf'))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
SSH_KEY_DIR = os.path.join(BASE_DIR, 'keys')
SERVER_KEY_DIR = os.path.join(SSH_KEY_DIR, 'server')
KEY = CONF.get('web', 'key')
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


class ServerError(Exception):
    pass


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


def get_object(model, **kwargs):
    try:
        the_object = model.objects.get(**kwargs)
    except ObjectDoesNotExist:
        raise ServerError('Object get %s failed.' % str(kwargs.values()))
    return the_object


def log_record(username, host):
    """Logging user command and output."""
    connect_log_dir = os.path.join(LOG_DIR, 'connect')
    timestamp_start = int(time.time())
    today = time.strftime('%Y%m%d', time.localtime(timestamp_start))
    time_now = time.strftime('%H%M%S', time.localtime(timestamp_start))
    today_connect_log_dir = os.path.join(connect_log_dir, today)
    log_filename = '%s_%s_%s.log' % (username, host, time_now)
    log_file_path = os.path.join(today_connect_log_dir, log_filename)
    pid = os.getpid()
    ip_list = []
    remote_ip = os.popen("who |grep `ps aux |gawk '{if ($2==%s) print $1}'` |gawk '{print $5}'|tr -d '()'" % pid).readlines()
    for ip in remote_ip:
        ip_list.append(ip.strip('\n'))
    ip_list = ','.join(list(set(ip_list)))

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

    log = Log(user=username, host=host, remote_ip=ip_list, log_path=log_file_path, start_time=datetime.now(), pid=pid)
    log_file.write('Starttime is %s\n' % datetime.now())
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
        timestamp_end = time.time()
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
        log_file.write('Endtime is %s' % datetime.now())
        log_file.close()
        log.is_finished = True
        log.log_finished = False
        log.end_time = datetime.now()
        log.save()


def get_user_host(username):
    """Get the hosts of under the user control."""
    hosts_attr = {}
    asset_all = user_perm_asset_api(username)
    for asset in asset_all:
        hosts_attr[asset.ip] = [asset.id, asset.comment]
    return hosts_attr


def get_user_hostgroup(username):
    """Get the hostgroups of under the user control."""
    groups_attr = {}
    group_all = user_perm_group_api(username)
    for group in group_all:
        groups_attr[group.name] = [group.id, group.comment]
    return groups_attr


def get_connect_item(username, ip):
    cryptor = PyCrypt(KEY)

    asset = get_object(Asset, ip=ip)
    port = asset.port

    if not asset.is_active:
        raise ServerError('Host %s is not active.' % ip)

    user = get_object(User, username=username)

    if not user.is_active:
        raise ServerError('User %s is not active.' % username)

    login_type_dict = {
        'L': user.ldap_pwd,
    }

    if asset.login_type in login_type_dict:
        password = cryptor.decrypt(login_type_dict[asset.login_type])
        return username, password, ip, port

    elif asset.login_type == 'M':
        username = asset.username
        password = cryptor.decrypt(asset.password)
        return username, password, ip, port

    else:
        raise ServerError('Login type is not in ["L", "M"]')


def verify_connect(username, part_ip):
    hosts_attr = get_user_host(username)
    hosts = hosts_attr.keys()
    ip_matched = [ip for ip in hosts if part_ip in ip]

    if len(ip_matched) > 1:
        for ip in ip_matched:
            print '%s -- %s' % (ip, hosts_attr[ip][1])
    elif len(ip_matched) < 1:
        color_print('No Permission or No host.', 'red')
    else:
        username, password, host, port = get_connect_item(username, ip_matched[0])
        connect(username, password, host, port, LOGIN_NAME)


def print_prompt():
    msg = """\033[1;32m###  Welcome Use JumpServer To Login. ### \033[0m
          1) Type \033[32mIP ADDRESS\033[0m To Login.
          2) Type \033[32mP/p\033[0m To Print The Servers You Available.
          3) Type \033[32mG/g\033[0m To Print The Server Groups You Available.
          4) Type \033[32mE/e\033[0m To Execute Command On Several Servers.
          5) Type \033[32mQ/q\033[0m To Quit.
          """
    print textwrap.dedent(msg)


def print_user_host(username):
    hosts_attr = get_user_host(username)
    hosts = hosts_attr.keys()
    hosts.sort()
    for ip in hosts:
        print '%s -- %s' % (ip, hosts_attr[ip][1])


def print_user_hostgroup(username):
    group_attr = get_user_hostgroup(username)
    groups = group_attr.keys()
    for g in groups:
        print '%s -- %s' % (g, group_attr[g][1])


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
    #channel.resize_pty(height=win_size[0], width=win_size[1])
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
        color_print('%s:' %ip, 'blue')
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
    hosts = []
    color_print("Input the Host IP(s),Separated by Commas, q/Q to Quit.\n \
                You can choose in the following IP(s), Use Linux / Unix glob.", 'green')
    print_user_host(LOGIN_NAME)
    while True:
        inputs = raw_input('\033[1;32mip(s)>: \033[0m')
        if inputs in ['q', 'Q']:
            break
        get_hosts = get_user_host(username).keys()
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
    try:
        while True:
            try:
                option = raw_input("\033[1;32mOpt or IP>:\033[0m ")
            except EOFError:
                print
                continue
            if option in ['P', 'p']:
                print_user_host(LOGIN_NAME)
                continue
            elif option in ['G', 'g']:
                print_user_hostgroup(LOGIN_NAME)
                continue
            elif option in ['E', 'e']:
                exec_cmd_servers(LOGIN_NAME)
            elif option in ['Q', 'q']:
                sys.exit()
            else:
                try:
                    verify_connect(LOGIN_NAME, option)
                except ServerError, e:
                    color_print(e, 'red')
    except IndexError:
        pass
