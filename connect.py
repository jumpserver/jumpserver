#coding: utf-8

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
    sys.exit()


CURRENT_DIR = os.path.abspath('.')
CONF = ConfigParser()
CONF.read(os.path.join(CURRENT_DIR, 'jumpserver.conf'))
LOG_DIR = os.path.join(CURRENT_DIR, 'logs')
SSH_KEY_DIR = os.path.join(CURRENT_DIR, 'keys')
SERVER_KEY_DIR = os.path.join(SSH_KEY_DIR, 'server')
KEY = CONF.get('web', 'key')
LOGIN_NAME = getpass.getuser()
#LOGIN_NAME = os.getlogin()


def green_print(string):
    print '\033[1;32m%s\033[0m' % string


def red_print(string):
    print '\033[1;31m%s\033[0m' % string


def alert_print(string):
    red_print('AlertError: %s' % string)
    time.sleep(2)
    sys.exit()


class ServerError(Exception):
    def __init__(self, error):
        self.error = error

    def __str__(self):
        return self.error

    __repr__ = __str__


class PyCrypt(object):
    """It's used to encrypt and decrypt password."""
    def __init__(self, key):
        self.key = key
        self.mode = AES.MODE_CBC

    def encrypt(self, text):
        cryptor = AES.new(self.key, self.mode, b'0000000000000000')
        length = 16
        count = len(text)
        if count < length:
            add = (length - count)
            text += ('\0' * add)
        elif count > length:
            add = (length - (count % length))
            text += ('\0' * add)
        ciphertext = cryptor.encrypt(text)
        return b2a_hex(ciphertext)

    def decrypt(self, text):
        cryptor = AES.new(self.key, self.mode, b'0000000000000000')
        plain_text = cryptor.decrypt(a2b_hex(text))
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


def posix_shell(chan, username, host):
    """
    Use paramiko channel connect server and logging.
    """
    connect_log_dir = os.path.join(LOG_DIR, 'connect')
    timestamp_start = int(time.time())
    today = time.strftime('%Y%m%d', time.localtime(timestamp_start))
    date_now = time.strftime('%Y%m%d%H%M%S', time.localtime(timestamp_start))

    today_connect_log_dir = os.path.join(connect_log_dir, today)
    log_filename = '%s_%s_%s.log' % (username, host, date_now)
    log_file_path = os.path.join(today_connect_log_dir, log_filename)

    try:
        user = User.objects.get(username=username)
        asset = Asset.objects.get(ip=host)
    except ObjectDoesNotExist:
        raise ServerError('user %s or asset %s does not exist.' % (username, host))

    pid = os.getpid()
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
    hosts_attr = {}
    try:
        user = User.objects.get(username=username)
    except ObjectDoesNotExist:
        raise ServerError("Username \033[1;31m%s\033[0m doesn't exist on Jumpserver." % username)
    else:
        perm_all = user.permission_set.all()
        for perm in perm_all:
            hosts_attr[perm.asset.ip] = [perm.asset.id, perm.asset.comment]
        hosts = hosts_attr.keys()
        hosts.sort()
        return hosts_attr, hosts


def get_connect_item(username, ip):
    cryptor = PyCrypt(KEY)

    try:
        asset = Asset.objects.get(ip=ip)
        port = asset.port
    except ObjectDoesNotExist:
        raise ServerError("Host %s does not exist." % ip)

    if not asset.is_active:
        raise ServerError('Host %s is not active.' % ip)

    try:
        user = User.objects.get(username=username)
    except ObjectDoesNotExist:
        raise ServerError('User %s does not exist.' % username)

    if not user.is_active:
        raise ServerError('User %s is not active.' % username)

    if asset.login_type == 'L':
        try:
            ldap_pwd = cryptor.decrypt(user.ldap_pwd)
        except TypeError:
            raise ServerError('Decrypt %s ldap password error.' % username)
        return 'L', username, ldap_pwd, ip, port
    elif asset.login_type == 'S':
        try:
            ssh_key_pwd = cryptor.decrypt(user.ssh_key_pwd2)
        except TypeError:
            raise ServerError('Decrypt %s ssh key password error.' % username)
        return 'S', username, ssh_key_pwd, ip, port
    elif asset.login_type == 'P':
        try:
            ssh_pwd = cryptor.decrypt(user.ssh_pwd)
        except TypeError:
            raise ServerError('Decrypt %s ssh password error.' % username)
        return 'P', username, ssh_pwd, ip, port
    elif asset.login_type == 'M':
        perms = asset.permission_set.filter(user=user)
        try:
            perm = perms[0]
        except IndexError:
            raise ServerError('Permission %s to %s does not exist.' % (username, ip))

        if perm.role == 'SU':
            username_super = asset.username_super
            try:
                password_super = cryptor.decrypt(asset.password_super)
            except TypeError:
                raise ServerError('Decrypt %s map to %s password in %s error.' % (username, username_super, ip))
            return 'M', username_super, password_super, ip, port

        elif perm.role == 'CU':
            username_common = asset.username_common
            try:
                password_common = asset.password_common
            except TypeError:
                raise ServerError('Decrypt %s map to %s password in %s error.' % (username, username_common, ip))
            return 'CU', username_common, password_common, ip, port

        else:
            raise ServerError('Perm in %s for %s map role is not in ["SU", "CU"].' % (ip, username))
    else:
        raise ServerError('Login type is not in ["L", "S", "P", "M"]')


def verify_connect(username, part_ip):
    ip_matched = []
    hosts_mix, hosts = get_user_host(username)
    for ip in hosts:
        if part_ip in ip:
            ip_matched.append(ip)

    if len(ip_matched) > 1:
        for ip in ip_matched:
            print '[%s] %s -- %s' % (hosts_mix[ip][0], ip, hosts_mix[ip][1])
    elif len(ip_matched) < 1:
        red_print('No Permission or No host.')
    else:
        login_type, username, password, host, port = get_connect_item(username, ip_matched[0])
        connect(username, password, host, port, LOGIN_NAME, login_type=login_type)


def print_prompt():
    msg = """\033[1;32m###  Welcome Use JumpServer To Login. ### \033[0m
          1) Type \033[32mIP ADDRESS\033[0m To Login.
          2) Type \033[32mP/p\033[0m To Print The Servers You Available.
          3) Type \033[32mE/e\033[0m To Execute Command On Several Servers.
          4) Type \033[32mQ/q\033[0m To Quit.
          """
    print textwrap.dedent(msg)


def print_user_host(username):
    hosts_attr, hosts = get_user_host(username)
    for ip in hosts:
        print '[%s] %s -- %s' % (hosts_attr[ip][0], ip, hosts_attr[ip][1])


def connect(username, password, host, port, login_name, login_type='L'):
    """
    Connect server.
    """
    ps1 = "PS1='[\u@%s \W]\$ '\n" % host
    login_msg = "clear;echo -e '\\033[32mLogin %s done. Enjoy it.\\033[0m'\n" % host
    user_key_file = os.path.join(SERVER_KEY_DIR, username)

    if os.path.isfile(user_key_file):
        key_filename = user_key_file
    else:
        key_filename = None

    # Make a ssh connection
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        if login_type == 'L':
            ssh.connect(host, port=port, username=username, password=password, key_filename=key_filename, compress=True)
        else:
            ssh.connect(host, port=port, username=username, password=password, compress=True)
    except paramiko.ssh_exception.AuthenticationException:
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
                pass
            elif option in ['Q', 'q']:
                sys.exit()
            else:
                try:
                    verify_connect(LOGIN_NAME, option)
                except ServerError, e:
                    red_print(e)
    except IndexError:
        pass