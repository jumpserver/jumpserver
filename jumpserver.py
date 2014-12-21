#coding: utf8

import socket
import sys
import os
import select
import time

try:
    import termios
    import tty
except ImportError:
    print 'Only postfix supported.'
    sys.exit()


CURRENT_DIR = os.path.abspath('.')
LOG_DIR = os.path.join(CURRENT_DIR, 'logs')


def posix_shell(chan, user, host):
    """
    Use paramiko channel connect server and logging.
    """
    today = time.strftime('%Y%m%d')
    today_log_dir = os.path.join(LOG_DIR, today)
    time_now = time.strftime('%H%M%S')
    log_filename = ''
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
                except socket.timeout:
                    pass

            if sys.stdin in r:
                x = os.read(sys.stdin.fileno(), 1)
                if len(x) == 0:
                    break
                chan.send(x)

    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)

