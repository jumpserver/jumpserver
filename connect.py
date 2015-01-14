# coding: utf-8

import socket
import sys
import os
import select
import time
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
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
from ConfigParser import ConfigParser
from django.core.exceptions import ObjectDoesNotExist

os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings'
django.setup()
from juser.models import User
from jasset.models import Asset
from jlog.models import Log

try:
    import termios
    import tty
except ImportError:
    print '\033[1;31mOnly postfix supported.\033[0m'
    time.sleep(3)
    sys.exit()

BASE_DIR = os.path.dirname(__file__)
CONF = ConfigParser()
CONF.read(os.path.join(BASE_DIR, 'jumpserver.conf'))
LOG_DIR = os.path.join(BASE_DIR, 'logs')
# Web generate user ssh_key dir.
SSH_KEY_DIR = os.path.join(BASE_DIR, 'keys')
# User upload the server key to this dir.
SERVER_KEY_DIR = os.path.join(SSH_KEY_DIR, 'server')
# The key of decryptor.
KEY = CONF.get('web', 'key')
# Login user.
LOGIN_NAME = getpass.getuser()
#LOGIN_NAME = os.getlogin()
USER_KEY_FILE = os.path.join(SERVER_KEY_DIR, LOGIN_NAME)

if not os.path.isfile(USER_KEY_FILE):
    USER_KEY_FILE = None


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


class PyCrypt(object):
    """This class used to encrypt and decrypt password."""

    def __init__(self, key):
        self.key = key
        self.mode = AES.MODE_CBC

    def encrypt(self, text):
        cryptor = AES.new(self.key, self.mode, b'0000000000000000')
        length = 16
        try:
            count = len(text)
        except TypeError:
            raise ServerError('Encrypt password error, TYpe error.')
        add = (length - (count % length))
        text += ('\0' * add)
        ciphertext = cryptor.encrypt(text)
        return b2a_hex(ciphertext)

    def decrypt(self, text):
        cryptor = AES.new(self.key, self.mode, b'0000000000000000')
        try:
            plain_text = cryptor.decrypt(a2b_hex(text))
        except TypeError:
            raise ServerError('Decrypt password error, TYpe error.')
        return plain_text.rstrip('\0')


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

    user = get_object(User, username=username)
    asset = get_object(Asset, ip=host)

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

    log = Log(user=user, asset=asset, log_path=log_file_path, start_time=timestamp_start, pid=pid)
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
        log_file.close()
        log.is_finished = True
        log.end_time = timestamp_end
        log.save()


def get_user_host(username):
    """Get the hosts of under the user control."""
    hosts_attr = {}
    try:
        user = User.objects.get(username=username)
    except ObjectDoesNotExist:
        raise ServerError("Username \033[1;31m%s\033[0m doesn't exist on Jumpserver." % username)
    else:
        perm_all = user.permission_set.all()
        for perm in perm_all:
            hosts_attr[perm.asset.ip] = [perm.asset.id, perm.asset.comment]
        return hosts_attr


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
        'S': user.ssh_key_pwd2,
        'P': user.ssh_pwd,
    }

    if asset.login_type in login_type_dict:
        password = cryptor.decrypt(login_type_dict[asset.login_type])

        return username, password, ip, port

    elif asset.login_type == 'M':
        perms = asset.permission_set.filter(user=user)
        if perms:
            perm = perms[0]
        else:
            raise ServerError('Permission %s to %s does not exist.' % (username, ip))

        if perm.role == 'SU':
            username_super = asset.username_super
            password_super = cryptor.decrypt(asset.password_super)
            return username_super, password_super, ip, port

        elif perm.role == 'CU':
            username_common = asset.username_common
            password_common = asset.password_common
            return username_common, password_common, ip, port

        else:
            raise ServerError('Perm in %s for %s map role is not in ["SU", "CU"].' % (ip, username))
    else:
        raise ServerError('Login type is not in ["L", "S", "P", "M"]')


def verify_connect(username, part_ip):
    hosts_attr = get_user_host(username)
    hosts = hosts_attr.keys()
    ip_matched = [ip for ip in hosts if part_ip in ip]

    if len(ip_matched) > 1:
        for ip in ip_matched:
            print '[%s] %s -- %s' % (hosts_attr[ip][0], ip, hosts_attr[ip][1])
    elif len(ip_matched) < 1:
        color_print('No Permission or No host.', 'red')
    else:
        username, password, host, port = get_connect_item(username, ip_matched[0])
        connect(username, password, host, port, LOGIN_NAME)


def print_prompt():
    msg = """\033[1;32m###  Welcome Use JumpServer To Login. ### \033[0m
          1) Type \033[32mIP ADDRESS\033[0m To Login.
          2) Type \033[32mP/p\033[0m To Print The Servers You Available.
          3) Type \033[32mE/e\033[0m To Execute Command On Several Servers.
          4) Type \033[32mQ/q\033[0m To Quit.
          """
    print textwrap.dedent(msg)


def print_user_host(username):
    hosts_attr = get_user_host(username)
    hosts = hosts_attr.keys()
    hosts.sort()
    for ip in hosts:
        print '[%s] %s -- %s' % (hosts_attr[ip][0], ip, hosts_attr[ip][1])


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
        ssh.connect(host, port=port, username=username, password=password, key_filename=USER_KEY_FILE, compress=True)
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
        ssh.connect(ip, port, username, password, key_filename=USER_KEY_FILE, timeout=5)
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
