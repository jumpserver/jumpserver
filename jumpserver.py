#!/usr/bin/python
# coding: utf-8


import os
import sys
import subprocess
import MySQLdb
import struct
import fcntl
import termios
import signal
import re
import time
from Crypto.Cipher import AES
from binascii import b2a_hex, a2b_hex
import ConfigParser
import paramiko
import pxssh

cur_dir = os.path.dirname(__file__)
sys.path.append('%s/webroot/AutoSa/' % cur_dir)
os.environ['DJANGO_SETTINGS_MODULE'] = 'AutoSa.settings'

from UserManage.models import User, Logs, Pid
from Assets.models import Assets


cf = ConfigParser.ConfigParser()
cf.read('%s/jumpserver.conf' % cur_dir)

db_host = cf.get('db', 'host')
db_port = cf.getint('db', 'port')
db_user = cf.get('db', 'user')
db_password = cf.get('db', 'password')
db_db = cf.get('db', 'db')
log_dir = os.path.join(cur_dir, 'logs')
user_table = cf.get('jumpserver', 'user_table')
assets_table = cf.get('jumpserver', 'assets_table')
assets_user_table = cf.get('jumpserver', 'assets_user_table')
key = cf.get('jumpserver', 'key')


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


def sigwinch_passthrough(sig, data):
    """This function use to set the window size of the terminal!"""
    winsize = getwinsize()
    try:
        foo.setwinsize(winsize[0], winsize[1])
    except:
        pass


def getwinsize():
    """This function use to get the size of the windows!"""
    if 'TIOCGWINSZ' in dir(termios):
        TIOCGWINSZ = termios.TIOCGWINSZ
    else:
        TIOCGWINSZ = 1074295912L  # Assume
    s = struct.pack('HHHH', 0, 0, 0, 0)
    x = fcntl.ioctl(sys.stdout.fileno(), TIOCGWINSZ, s)
    return struct.unpack('HHHH', x)[0:2]


# def connect_db(user, passwd, db, host='127.0.0.1', port=3306):
#     """This function connect db and return db and cursor"""
#     db = MySQLdb.connect(host=host,
#                          port=port,
#                          user=user,
#                          passwd=passwd,
#                          db=db,
#                          charset='utf8')
#     cursor = db.cursor()
#     return db, cursor


def run_cmd(cmd):
    """run command and return stdout"""
    pipe = subprocess.Popen(cmd, 
                            shell=True, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
    if pipe.stdout:
        stdout = pipe.stdout.read().strip()
        pipe.wait()
        return stdout
    if pipe.stderr:
        stderr = pipe.stderr.read()
        pipe.wait()
        return stderr


def connect(host, port, user, password):
    """Use pexpect module to connect other server."""
    log_date_dir = '%s/%s' % (log_dir, time.strftime('%Y%m%d'))
    if not os.path.isdir(log_date_dir):
        os.mkdir(log_date_dir)
    structtime_start = time.localtime()
    datetime_start = time.strftime('%Y%m%d%H%M%S', structtime_start)
    logtime_start = time.strftime('%Y/%m/%d %H:%M:%S', structtime_start)
    timestamp_start = int(time.mktime(structtime_start))
    logfile_name = "%s/%s_%s_%s" % (log_date_dir, host, user, datetime_start)

    try:
        global foo
        foo = pxssh.pxssh()
        foo.login(host, user, password, port=port, auto_prompt_reset=False)
        log = Logs(user=user, host=host, logfile=logfile_name, start_time=timestamp_start)  # 日志信息记录到数据库
        log.save()
        pid = Pid(ppid=os.getpid(), cpid=foo.pid)
        pid.save()

        logfile = open(logfile_name, 'a')  # 记录日志文件
        logfile.write('\n%s\n' % logtime_start)
        foo.logfile = logfile
        foo.sendline('')
        signal.signal(signal.SIGWINCH, sigwinch_passthrough)

        foo.interact(escape_character=chr(28))
        logfile.write('\n%s' % time.strftime('%Y/%m/%d %H:%M:%S'))
        log.finish = 1
        log.end_time = int(time.time())
        log.save()
    except pxssh.ExceptionPxssh as e:
        print('登录失败: %s' % e)
    except KeyboardInterrupt:
        foo.logout()
        log.finish = 1
        log.end_time = int(time.time())
        log.save()


def ip_all_select(username):
    """select all the server of the user can control."""
    ip_all = []
    ip_all_dict = {}
    user = User.objects.get(username=username)
    all_assets_user = user.assetsuser_set.all()
    for assets_user in all_assets_user:
        ip_all.append(assets_user.aid.ip)
        ip_all_dict[assets_user.aid.ip] = assets_user.aid.comment

    return ip_all, ip_all_dict


def sth_select(username='', ip=''):
    """if username: return password elif ip return port"""
    if username:
        user = User.objects.get(username=username)
        ldap_password = user.ldap_password
        return ldap_password

    if ip:
        asset = Assets.objects.get(ip=ip)
        port = asset.port
        return port
    return None


def remote_exec_cmd(host, user, cmd):
    jm = PyCrypt(key)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    port = sth_select(ip=host)
    password = jm.decrypt(sth_select(username=username))
    try:
        ssh.connect(host, port, user, password)
    except paramiko.AuthenticationException:
        print 'Password Error .'
        return None
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print '\033[32m' + '#'*15 + ' ' + host + ' ' + '#'*15 + '\n' + '\033[0m'
    output = stdout.read()
    error = stderr.read()
    if output:
        print output
    if error:
        print error
    print '\033[32m' + '#'*15 + '  End result  ' + '#'*15 + '\n' + '\033[0m'
    ssh.close()


def match_ip(all_ip, string):
    ip_matched = []
    pattern = re.compile(r'%s' % string)

    for ip in all_ip:
        if pattern.search(ip):
            ip_matched.append(ip)
    return ip_matched


def print_prompt():
        print """
\033[1;32m###  Welcome Use JumpServer To Login. ### \033[0m
1) Type \033[32mIP ADDRESS\033[0m To Login.
2) Type \033[32mP/p\033[0m To Print The Servers You Available.
3) Type \033[32mE/e\033[0m To Execute Command On Several Servers.
4) Type \033[32mQ/q\033[0m To Quit.
"""


def print_your_server(username):
    ip_all, ip_all_dict = ip_all_select(username)
    for ip in ip_all:
        if ip_all_dict[ip]:
            print "%s -- %s" % (ip, ip_all_dict[ip])
        else:
            print ip


def exec_cmd_servers(username):
    print '\nInput the \033[32mHost IP(s)\033[0m,Separated by Commas, q/Q to Quit.\n'
    while True:
        hosts = raw_input('\033[1;32mip(s)>: \033[0m')
        if hosts in ['q', 'Q']:
            break
        hosts = hosts.split(',')
        hosts.append('')
        hosts = list(set(hosts))
        hosts.remove('')
        ip_all, ip_all_dict = ip_all_select(username)
        no_perm = set(hosts)-set(ip_all)
        if no_perm:
            print "You have NO PERMISSION on %s..." % list(no_perm)
            continue
        print '\nInput the \033[32mCommand\033[0m , The command will be Execute on servers, q/Q to quit.\n'
        while True:
            cmd = raw_input('\033[1;32mCmd(s): \033[0m')
            if cmd in ['q', 'Q']:
                break
            for host in hosts:
                remote_exec_cmd(host, username, cmd)


def connect_one(username, option):
    ip_input = option.strip()
    ip_all, ip_all_dict = ip_all_select(username)
    ip_matched = match_ip(ip_all, ip_input)
    ip_len = len(ip_matched)
    ip = ''
    if ip_len >= 1:
        if ip_len == 1:
            ip = ip_matched[0]
        else:
            if ip_input in ip_matched:
                ip = ip_input
            else:
                for one_ip in ip_matched:
                    print one_ip
        if ip:
            password = jm.decrypt(sth_select(username=username))
            port = sth_select(ip=ip)
            print "Connecting %s ..." % ip
            connect(ip, port, username, password)
    else:
        print '\033[31mNo permision .\033[0m'


if __name__ == '__main__':
    username = run_cmd('whoami')
    jm = PyCrypt(key)
    print_prompt()
    try:
        while True:
            try:
                option = raw_input("\033[1;32mOpt or IP>:\033[0m ")
            except EOFError:
                print
                continue
            if option in ['P', 'p']:
                print_your_server(username)
                continue
            elif option in ['e', 'E']:
                exec_cmd_servers(username)
            elif option in ['q', 'Q']:
                sys.exit()
            else:
                connect_one(username, option)
    #except (BaseException, Exception):
    except IndexError:
        print "Exit."
        sys.exit()