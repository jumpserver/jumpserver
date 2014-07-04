#!/usr/bin/python
# coding: utf-8

"""
This script is used to let server to be a jump server.
业务逻辑： 用户通过自己这套账号密码连接到跳板机，
然后从跳板机链接到各个业务Server, 该脚本可以实现
登录到其他业务机的功能，并且针对不同的用户实现不
同的授权的， 可以讲用户的负责的主机print出来，用
户的权限密码存放在数据库中。现在要考虑是否得用ex-
pect模块，还是os.command.用户选择别的，或者Ctrl+D,
Ctrl+C直接退出。改脚本二进制方式存放。

使用方法：
1. 把该文件放到合适的问题如/tmp，保证所有用户都能访问的到。
2. vim /etc/profile.d/jump.sh
   #/bin/bash
   python /tmp/jump.py
   if [ $USER == 'root' ]:
       echo ""
   else
       exit
   fi
   
数据库表结构：
user
id  username  password 

server
id  ip  port

user_server
id user_id server_id

CREATE TABLE user(id INT NOT NULL,
                  username VARCHAR(30),
                  password VARCHAR(30),
                  PRIMARY KEY(id)
                  ) ENGINE=INNODB;
           
CREATE TABLE server(id INT NOT NULL,
                    ip VARCHAR(20),
                    port SMALLINT,
                    PRIMARY KEY(id)
                    ) ENGINE=INNODB;
                    
CREATE TABLE user_server(id INT NOT NULL,
                        user_id INT,
                        server_id INT,
                        PRIMARY KEY(id),
                        FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE ON UPDATE CASCADE,
                        FOREIGN KEY(user_id) REFERENCES user(id) ON DELETE CASCADE ON UPDATE CASCADE
                        ) ENGINE=INNODB;
                        
select * from user t1, server t2, user_server t3 where t1.username='ldapuser' and t1.id=t3.user_id and t2.id = t3.server_id;
                        
"""

import os
import sys
import subprocess
import pexpect
import struct
import fcntl
import termios
import signal
import MySQLdb
import re

"""
#Test user
host = '192.168.2.143'
port = 22
user = 'ldapuser'
password = 'redhat'
"""

db_host = '127.0.0.1'
db_user = 'root'
db_password = 'redhat'
db_db = 'jump'
db_port = 3306


def sigwinch_passthrough (sig, data):
    winsize = getwinsize()
    global bar
    bar.setwinsize(winsize[0],winsize[1])

def getwinsize():
    if 'TIOCGWINSZ' in dir(termios):
        TIOCGWINSZ = termios.TIOCGWINSZ
    else:
        TIOCGWINSZ = 1074295912L # Assume
    s = struct.pack('HHHH', 0, 0, 0, 0)
    x = fcntl.ioctl(sys.stdout.fileno(), TIOCGWINSZ, s)
    return struct.unpack('HHHH', x)[0:2]
    
def progress(second, nums, sym='.'):
    for i in range(nums):
        os.write(1, sym)
        time.sleep(second)
    sys.stdout.flush()

def connect_db(user, passwd, db, host='127.0.0.1', port=3306):
    db = MySQLdb.connect(host=host,
                        port=port,
                        user=user,
                        passwd=passwd,
                        db=db)
    cursor = db.cursor()
    return (db, cursor)

def run_cmd(cmd):
    pipe = subprocess.Popen(cmd, 
                            shell=True, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE)
    if pipe.stdout:
        return pipe.stdout.read().strip()
    if pipe.stderr:
        return pipe.stdout.read()

def is_ip(ip):
    ip_re = re.compile(r'^(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[0-9]{1,2})(\.(25[0-5]|2[0-4][0-9]|1[0-9][0-9]|[0-9]{1,2})){3}$')
    match = ip_re.match(ip)
    if match:
        return True
    else:
        return False
        
def connect(host, port, user, password ):
    foo = pexpect.spawn('ssh -p %s %s@%s' % (port, user, host))
    while True:
        index = foo.expect(['continue', 
                            'assword', 
                            pexpect.EOF, 
                            pexpect.TIMEOUT], timeout=3)
        if index == 0:
            foo.sendline('yes')
            continue
        elif index == 1:
            foo.sendline(password)
        
        index = foo.expect([']', 
                            'assword', 
                            pexpect.EOF, 
                            pexpect.TIMEOUT], timeout=3)
        if index == 0:
            signal.signal(signal.SIGWINCH, sigwinch_passthrough)
            size = getwinsize()
            foo.setwinsize(size[0], size[1])
            foo.interact()
            print "Login success!"
            break
        else:
            print "Login failed, please contact system administrator!"
            break

def ip_all_select(username):
    ip_all = []
    db, cursor = connect_db(db_user, db_password, db_db, db_host, db_port)
    cursor.execute('select t2.ip from user t1, server t2, user_server t3 where t1.username="%s" and t1.id=t3.user_id and t2.id = t3.server_id;' % username)
    ip_all_record = cursor.fetchall()
    if ip_all_record:
        for record in ip_all_record:
            ip_all.append(record[0])
    db.close()
    return ip_all

def sth_select(username='', ip=''):
    db, cursor = connect_db(db_user, db_password, db_db, db_host, db_port)
    if username:
        cursor.execute('select password from user where username="%s"' % username)
        try:
            password = cursor.fetchone()[0]
        except IndexError:
            password = ''
        return password
    if  ip:
        cursor.execute('select port from server where ip="%s"' % ip)
        try:
            port = cursor.fetchone()[0]
        except IndexError:
            port = 22
        return port
    
    return Null
            
if __name__ == '__main__':
    username = run_cmd('whoami')
    print username
    while True:
        option = raw_input("""
        Welcome Use JumpServer To Login.
        1) Type L/l To Login.
        2) Type P/p To Print The Servers You Available.
        3) Other To Quit.
        Your Choince: """)
        if option in ['P', 'p']:
            ip_all = ip_all_select(username)
            for ip in ip_all:
                print '\n' * 2
                print ip
                print '\n' * 2
            continue
        elif option not in ['L', 'l']:
            sys.exit()
            
        try:
            while True:
                ip = raw_input('Please input the Host IP: ')
                if is_ip(ip) and ip in ip_all_select(username):
                    password = sth_select(username=username)
                    port = sth_select(ip=ip)
                    print "Connecting %s ." % ip
                    connect(ip, port, username, password)
                elif ip == 'admin':
                    break
                elif ip in ['Q', 'q']:
                    break
                else:
                    print 'No permision.'
                    continue            
        except (BaseException,Exception):
            print "Error!"
            sys.exit()