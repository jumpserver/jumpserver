#!/usr/bin/python
# coding: utf-8

import subprocess
import time
import os
import sys
import MySQLdb
from smtplib import SMTP, SMTPAuthenticationError, SMTPConnectError, SMTPSenderRefused
import ConfigParser
import socket
import fcntl
import struct
import readline

jms_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(jms_dir)


def bash(cmd):
    """
    run a bash shell command
    执行bash命令
    """
    return subprocess.call(cmd, shell=True)


def color_print(msg, color='red', exits=False):
    """
    Print colorful string.
    颜色打印字符或者退出
    """
    color_msg = {'blue': '\033[1;36m%s\033[0m',
                 'green': '\033[1;32m%s\033[0m',
                 'yellow': '\033[1;33m%s\033[0m',
                 'red': '\033[1;31m%s\033[0m',
                 'title': '\033[30;42m%s\033[0m',
                 'info': '\033[32m%s\033[0m'}
    msg = color_msg.get(color, 'red') % msg
    print msg
    if exits:
        time.sleep(2)
        sys.exit()
    return msg


def get_ip_addr(ifname='eth0'):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,
            struct.pack('256s', ifname[:15])
        )[20:24])
    except:
        ips = os.popen("LANG=C ifconfig | grep \"inet addr\" | grep -v \"127.0.0.1\" | awk -F \":\" '{print $2}' | awk '{print $1}'").readlines()
        if len(ips) > 0:
            return ips[0]
    return ''


class PreSetup(object):
    def __init__(self):
        self.db_host = '127.0.0.1'
        self.db_port = 3306
        self.db_user = 'jumpserver'
        self.db_pass = '5Lov@wife'
        self.db = 'jumpserver'
        self.mail_host = 'smtp.qq.com'
        self.mail_port = 25
        self.mail_addr = 'hello@jumpserver.org'
        self.mail_pass = ''
        self.ip = ''

    def write_conf(self, conf_file=os.path.join(jms_dir, 'jumpserver.conf')):
        color_print('开始写入配置文件', 'green')
        conf = ConfigParser.ConfigParser()
        conf.read(conf_file)
        conf.set('base', 'url', 'http://%s' % self.ip)
        conf.set('db', 'host', self.db_host)
        conf.set('db', 'port', self.db_port)
        conf.set('db', 'user', self.db_user)
        conf.set('db', 'password', self.db_pass)
        conf.set('db', 'database', self.db)
        conf.set('websocket', 'web_socket_host', '%s:3000' % self.ip)
        conf.set('mail', 'email_host', self.mail_host)
        conf.set('mail', 'email_port', self.mail_port)
        conf.set('mail', 'email_host_user', self.mail_addr)
        conf.set('mail', 'email_host_password', self.mail_pass)

        with open(conf_file, 'w') as f:
            conf.write(f)

    def _setup_mysql(self):
        color_print('开始安装设置mysql (请手动设置mysql安全)', 'green')
        color_print('默认用户名: %s 默认密码: %s' % (self.db_user, self.db_pass), 'green')
        bash('yum -y install mysql-server')
        bash('service mysqld start')
        bash('mysql -e "create database %s default charset=utf8"' % self.db)
        bash('mysql -e "grant all on %s.* to \'%s\'@\'%s\' identified by \'%s\'"' % (self.db,
                                                                                     self.db_user,
                                                                                     self.db_host,
                                                                                     self.db_pass))

    @staticmethod
    def _set_env():
        color_print('开始关闭防火墙和selinux', 'green')
        bash('service iptables stop && chkconfig iptables off && setenforce 0')

    def _test_db_conn(self):
        try:
            MySQLdb.connect(host=self.db_host, port=int(self.db_port),
                            user=self.db_user, passwd=self.db_pass, db=self.db)
            color_print('连接数据库成功', 'green')
            return True
        except MySQLdb.OperationalError, e:
            color_print('数据库连接失败 %s' % e, 'red')
            return False

    def _test_mail(self):
        try:
            smtp = SMTP(self.mail_host, port=self.mail_port, timeout=2)
            smtp.login(self.mail_addr, self.mail_pass)
            smtp.sendmail(self.mail_addr, (self.mail_addr, ),
                          '''From:%s\r\nTo:%s\r\nSubject:Jumpserver Mail Test!\r\n\r\n  Mail test passed!\r\n''' %
                          (self.mail_addr, self.mail_addr))
            smtp.quit()
            return True

        except Exception, e:
            color_print(e, 'red')
            skip = raw_input('是否跳过(y/n) [n]? : ')
            if skip == 'y':
                return True
            return False

    @staticmethod
    def _rpm_repo():
        color_print('开始安装epel源', 'green')
        bash('yum -y install epel-release')

    @staticmethod
    def _depend_rpm():
        color_print('开始安装依赖rpm包', 'green')
        bash('yum -y install git python-pip mysql-devel gcc automake autoconf python-devel vim sshpass')

    @staticmethod
    def _require_pip():
        color_print('开始安装依赖pip包', 'green')
        bash('pip install -r requirements.txt')

    def _input_ip(self):
        ip = raw_input('\n请输入您服务器的IP地址，用户浏览器可以访问 [%s]: ' % get_ip_addr()).strip()
        self.ip = ip if ip else get_ip_addr()

    def _input_mysql(self):
        while True:
            mysql = raw_input('是否安装新的MySQL服务器? (y/n) [y]: ')
            if mysql != 'n':
                self._setup_mysql()
            else:
                db_host = raw_input('请输入数据库服务器IP [127.0.0.1]: ').strip()
                db_port = raw_input('请输入数据库服务器端口 [3306]: ').strip()
                db_user = raw_input('请输入数据库服务器用户 [root]: ').strip()
                db_pass = raw_input('请输入数据库服务器密码: ').strip()
                db = raw_input('请输入使用的数据库 [jumpserver]: ').strip()

                if db_host: self.db_host = db_host
                if db_port: self.db_port = db_port
                if db_user: self.db_user = db_user
                if db_pass: self.db_pass = db_pass
                if db: self.db = db

            if self._test_db_conn():
                break

            print

    def _input_smtp(self):
        while True:
            self.mail_host = raw_input('请输入SMTP地址: ').strip()
            mail_port = raw_input('请输入SMTP端口 [25]: ').strip()
            self.mail_addr = raw_input('请输入账户: ').strip()
            self.mail_pass = raw_input('请输入密码: ').strip()

            if mail_port: self.mail_port = int(mail_port)

            if self._test_mail():
                color_print('\n\t请登陆邮箱查收邮件, 然后确认是否继续安装\n', 'green')
                smtp = raw_input('是否继续? (y/n) [y]: ')
                if smtp == 'n':
                    continue
                else:
                    break
            print

    def start(self):
        # self._rpm_repo()
        # self._depend_rpm()
        # self._require_pip()
        color_print('请务必先查看wiki https://github.com/ibuler/jumpserver/wiki/Quickinstall')
        time.sleep(3)
        self._set_env()
        self._input_ip()
        self._input_mysql()
        self._input_smtp()
        self.write_conf()
        os.system('python %s' % os.path.join(jms_dir, 'install/next.py'))


if __name__ == '__main__':
    pre_setup = PreSetup()
    pre_setup.start()
