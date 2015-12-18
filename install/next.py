#!/usr/bin/python
# coding: utf-8

import sys
import os
import MySQLdb
import smtplib
import ConfigParser
import django
from django.core.management import execute_from_command_line
import socket
from smtplib import SMTP, SMTPAuthenticationError, SMTPConnectError
import fcntl
import struct

jms_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(jms_dir)

os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings'
if django.get_version() != '1.6':
    setup = django.setup()

from jumpserver.api import chown, bash, PyCrypt, ServerError, get_object, mkdir
from juser.user_api import db_add_user, server_add_user
from connect import color_print


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


class Setup(object):
    """
    安装jumpserver向导
    """
    def __init__(self):
        self.db_host = '127.0.0.1'
        self.db_port = 3306
        self.db_user = 'jumpserver'
        self.db_pass = 'mysql234'
        self.db = 'jumpserver'
        self.mail_host = 'smtp.qq.com'
        self.mail_port = 25
        self.mail_addr = 'hello@jumpserver.org'
        self.mail_pass = ''
        self.ip = ''
        self.admin_user = 'admin'
        self.admin_pass = 'Lov@jms'

    def write_conf(self, conf_file=os.path.join(jms_dir, 'jumpserver.conf')):
        color_print('开始写入配置文件', 'green')
        conf = ConfigParser.ConfigParser()
        conf.read(conf_file)
        conf.set('base', 'url', 'http://%s' % self.ip)
        conf.set('db', 'host', self.db_host)
        conf.set('db', 'port', self.db_port)
        conf.set('db', 'user', self.db_user)
        conf.set('db', 'pass', self.db_pass)
        conf.set('db', 'database', self.db)
        conf.set('websocket', 'web_socket_host', '%s: 3000' % self.ip)
        conf.set('mail', 'email_host', self.mail_host)
        conf.set('mail', 'email_port', self.mail_port)
        conf.set('mail', 'email_host_user', self.mail_addr)
        conf.set('mail', 'email_host_password', self.mail_pass)

        with open(conf_file, 'w') as f:
            conf.write(f)

    def _setup_mysql(self):
        color_print('开始安装设置mysql (请手动设置mysql安全)', 'green')
        bash('yum -y install mysql-server')
        bash('service mysqld start')
        bash('mysql -e "create database %s default charset=utf8"' % self.db)
        bash('mysql -e "grant all on %s.* to \'%s\'@\'%s\' identified by \'%s\'"' % (self.db,
                                                                                     self.db_user,
                                                                                     self.db_host,
                                                                                     self.db_pass))

    @staticmethod
    def _pull():
        color_print('开始更新jumpserver', 'green')
        bash('git pull')
        os.chdir(jms_dir)
        mkdir('logs', mode=0777)
        mkdir('keys', mode=0777)

    @staticmethod
    def _set_env():
        color_print('开始关闭防火墙和selinux', 'green')
        bash('service iptables stop && chkconfig iptables off && setenforce 0')

    def _test_db_conn(self):
        try:
            MySQLdb.connect(host=self.db_host, port=self.db_port,
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

        except (SMTPAuthenticationError, socket.timeout), e:
            color_print(e, 'red')
            return False

    def _input_ip(self):
        ip = raw_input('\n请输入您服务器的IP地址，用户浏览器可以访问 [%s]: ' % get_ip_addr())
        self.ip = ip if ip else get_ip_addr()

    def _input_mysql(self):
        while True:
            db_host = raw_input('请输入数据库服务器IP [127.0.0.1]: ')
            db_port = raw_input('请输入数据库服务器端口 [3306]: ')
            db_user = raw_input('请输入数据库服务器用户 [root]: ')
            db_pass = raw_input('请输入数据库服务器密码: ')
            db = raw_input('请输入使用的数据库 [jumpserver]: ')

            if db_host: self.db_host = db_host
            if db_port: self.db_port = db_port
            if db_user: self.db_user = db_user
            if db_pass: self.db_pass = db_pass
            if db: self.db = db

            mysql = raw_input('是否使用已经存在的数据库服务器? (y/n) [n]: ')

            if mysql != 'y':
                self._setup_mysql()

            if self._test_db_conn():
                break

            print

    def _input_smtp(self):
        while True:
            self.mail_host = raw_input('请输入SMTP地址: ').strip()
            self.mail_port = int(raw_input('请输入SMTP端口: ').strip())
            self.mail_addr = raw_input('请输入账户: ').strip()
            self.mail_pass = raw_input('请输入密码: ').strip()

            if self._test_mail():
                color_print('\n\t请登陆邮箱查收邮件, 然后确认是否继续安装\n', 'green')
                smtp = raw_input('是否继续? (y/n) [y]: ')
                if smtp == 'n':
                    continue
                else:
                    break
            print

    def _input_admin(self):
        while True:
            self.admin_user = raw_input('请输入管理员用户名 [%s]: ' % self.admin_user).strip()
            self.admin_pass = raw_input('请输入管理员密码: ').strip()
            admin_pass_again = raw_input('请再次输入管理员密码: ').strip()

            if self.admin_pass != admin_pass_again:
                color_print('两次密码不相同请重新输入')
            else:
                break
            print

    @staticmethod
    def _sync_db():
        os.chdir(jms_dir)
        execute_from_command_line(['manage.py', 'syncdb', '--noinput'])

    def _create_admin(self):
        db_add_user(username=self.admin_user, password=self.admin_pass, role='SU', name='admin', groups='',
                    admin_groups='', email='admin@jumpserver.org', uuid='MayBeYouAreTheFirstUser', is_active=True)
        server_add_user(self.admin_user, self.admin_user, ssh_key_login_need=False)

    def start(self):
        print "开始安装Jumpserver, 要求环境为 CentOS 6.5 x86_64"
        self._pull()
        self._input_ip()
        self._input_mysql()
        self._input_smtp()
        self._sync_db()
        self.write_conf()
        self._input_admin()
        self._create_admin()


if __name__ == '__main__':
    setup = Setup()
    setup.start()
