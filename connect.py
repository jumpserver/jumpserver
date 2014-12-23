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
from django.core.exceptions import ObjectDoesNotExist
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex

os.environ['DJANGO_SETTINGS_MODULE'] = 'AutoSa.settings'
django.setup()

from juser.models import User, Group
from jasset.models import Asset, IDC
from jpermission.models import Permission

try:
    import termios
    import tty
except ImportError:
    print '\033[1;31mOnly postfix supported.\033[0m'
    sys.exit()


CURRENT_DIR = os.path.abspath('.')
LOG_DIR = os.path.join(CURRENT_DIR, 'logs')


def green_print(string):
    print '\033[1;32m%s\033[0m' % string


def red_print(string):
    print '\033[1;31m%s\033[0m' % string


def alert_print(string):
    red_print('AlertError: %s' % string)
    time.sleep(2)
    sys.exit()


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


def posix_shell(chan, user, host):
    """
    Use paramiko channel connect server and logging.
    """
    connect_log_dir = os.path.join(LOG_DIR, 'connect')
    today = time.strftime('%Y%m%d')
    date_now = time.strftime('%Y%m%d%H%M%S')
    today_connect_log_dir = os.path.join(connect_log_dir, today)
    log_filename = '%s_%s_%s.log' % (user, host, date_now)
    log_file_path = os.path.join(today_connect_log_dir, log_filename)

    if not os.path.isdir(today_connect_log_dir):
        try:
            os.makedirs(today_connect_log_dir)
        except OSError:
            alert_print('Create %s failed, Please modify %s permission.' % (today_connect_log_dir, connect_log_dir))

    try:
        log = open(log_file_path, 'a')
    except IOError:
        alert_print('Create logfile failed, Please modify %s permission.' % today_connect_log_dir)

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
                    log.write(x)
                    log.flush()
                except socket.timeout:
                    pass

            if sys.stdin in r:
                x = os.read(sys.stdin.fileno(), 1)
                if len(x) == 0:
                    break
                chan.send(x)

    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
        log.close()


def get_host_all(username):
    host_all = {}
    try:
        user = User.objects.get(username=username)
    except AttributeError:
        red_print("Don't Use Root To Do That or User isn't Exist.")
    else:
        perm_all = user.permission_set.all()
        for perm in perm_all:
            host_all[perm.asset.ip] = perm.asset.comment
            return host_all


def print_prompt():
    msg = """
          \033[1;32m###  Welcome Use JumpServer To Login. ### \033[0m
          1) Type \033[32mIP ADDRESS\033[0m To Login.
          2) Type \033[32mP/p\033[0m To Print The Servers You Available.
          3) Type \033[32mE/e\033[0m To Execute Command On Several Servers.
          4) Type \033[32mQ/q\033[0m To Quit.
          """
    print textwrap.dedent(msg)


def print_user_host(username):
    host_all = get_host_all(username)
    for ip, comment in host_all.items():
        print '%s -- %s' % (ip, comment)


def connect(username, password, host, port):
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
    except paramiko.ssh_exception.AuthenticationException:
        alert_print('Host Password Error, Please Correct it.')
    except socket.error:
        alert_print('Connect SSH Socket Port Error, Please Correct it.')

    # Make a channel and set windows size
    global channel
    channel = ssh.invoke_shell()
    win_size = get_win_size()
    channel.resize_pty(height=win_size[0], width=win_size[1])
    try:
        signal.signal(signal.SIGWINCH, set_win_size)
    except:
        pass

    # Set PS1 and msg it
    channel.send(ps1)
    channel.send(login_msg)
    print channel.get_name()

    # Make ssh interactive tunnel
    posix_shell(channel, username, host)

    # Shutdown channel socket
    channel.close()
    ssh.close()


if __name__ == '__main__':
    username = os.getlogin()
    print_prompt()
    try:
        while True:
            try:
                option = raw_input("\033[1;32mOpt or IP>:\033[0m ")
            except EOFError:
                continue
            if option in ['P', 'p']:
                print_user_host()
                continue
            elif option in ['E', 'e']:
                pass
            elif option in ['Q', 'q']:
                sys.exit()
            else:
                pass
    except IndexError:
        pass


