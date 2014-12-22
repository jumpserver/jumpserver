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
    connect('guanghongwei', 'Lov@j1ax1n', '172.16.1.122', 2001)

