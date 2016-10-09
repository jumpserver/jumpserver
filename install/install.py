#!/usr/bin/python
# coding: utf-8

import time
import os
import sys
from smtplib import SMTP, SMTP_SSL, SMTPAuthenticationError, SMTPConnectError, SMTPSenderRefused
import ConfigParser
import socket
import random
import string

import re
import platform
import shlex

jms_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(jms_dir)


def bash(cmd):
    """
    run a bash shell command
    执行bash命令
    """
    return shlex.os.system(cmd)


def valid_ip(ip):
    if ('255' in ip) or (ip == "0.0.0.0"):
        return False
    else:
        return True


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


def get_ip_addr():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        if_data = ''.join(os.popen("LANG=C ifconfig").readlines())
        ips = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', if_data, flags=re.MULTILINE)
        ip = filter(valid_ip, ips)
        if ip:
            return ip[0]
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
        self.key = ''.join(random.choice(string.ascii_lowercase + string.digits) \
                           for _ in range(16))
        self.dist = platform.linux_distribution()[0].lower()
        self.version = platform.linux_distribution()[1]

    @property
    def _is_redhat(self):
        if self.dist.startswith("centos") or self.dist.startswith("red") or self.dist == "fedora" or self.dist == "oracle" or self.dist == "amazon linux ami":
            return True

    @property
    def _is_centos7(self):
        if self.dist.startswith("centos") and self.version.startswith("7"):
            return True

    @property
    def _is_fedora_new(self):
        if self.dist == "fedora" and int(self.version) >= 20:
            return True

    @property
    def _is_ubuntu(self):
        if self.dist == "ubuntu" or self.dist == "debian":
            return True

    def check_platform(self):
        if not (self._is_redhat or self._is_ubuntu):
            print(u"支持的平台: CentOS, RedHat, Fedora, Oracle Linux, Debian, Ubuntu, Amazon Linux, 暂不支持其他平台安装.")
            exit()

    @staticmethod
    def check_bash_return(ret_code, error_msg):
        if ret_code != 0:
            color_print(error_msg, 'red')
            exit()

    def write_conf(self, conf_file=os.path.join(jms_dir, 'jumpserver.conf')):
        color_print('开始写入配置文件', 'green')
        conf = ConfigParser.ConfigParser()
        conf.read(conf_file)
        conf.set('base', 'url', 'http://%s' % self.ip)
        conf.set('base', 'key', self.key)
        conf.set('db', 'host', self.db_host)
        conf.set('db', 'port', self.db_port)
        conf.set('db', 'user', self.db_user)
        conf.set('db', 'password', self.db_pass)
        conf.set('db', 'database', self.db)
        conf.set('mail', 'email_host', self.mail_host)
        conf.set('mail', 'email_port', self.mail_port)
        conf.set('mail', 'email_host_user', self.mail_addr)
        conf.set('mail', 'email_host_password', self.mail_pass)

        with open(conf_file, 'w') as f:
            conf.write(f)

    def _setup_mysql(self):
        color_print('开始安装设置mysql (请手动设置mysql安全)', 'green')
        color_print('默认用户名: %s 默认密码: %s' % (self.db_user, self.db_pass), 'green')
        if self._is_redhat:
            if self._is_centos7 or self._is_fedora_new:
                ret_code = bash('yum -y install mariadb-server mariadb-devel')
                self.check_bash_return(ret_code, "安装mysql(mariadb)失败, 请检查安装源是否更新或手动安装！")

                bash('systemctl enable mariadb.service')
                bash('systemctl start mariadb.service')
            else:
                ret_code = bash('yum -y install mysql-server')
                self.check_bash_return(ret_code, "安装mysql失败, 请检查安装源是否更新或手动安装！")

                bash('service mysqld start')
                bash('chkconfig mysqld on')
            bash('mysql -e "create database %s default charset=utf8"' % self.db)
            bash('mysql -e "grant all on %s.* to \'%s\'@\'%s\' identified by \'%s\'"' % (self.db,
                                                                                         self.db_user,
                                                                                         self.db_host,
                                                                                         self.db_pass))
        if self._is_ubuntu:
            cmd1 = "echo mysql-server mysql-server/root_password select '' | debconf-set-selections"
            cmd2 = "echo mysql-server mysql-server/root_password_again select '' | debconf-set-selections"
            cmd3 = "apt-get -y install mysql-server"
            ret_code = bash('%s; %s; %s' % (cmd1, cmd2, cmd3))
            self.check_bash_return(ret_code, "安装mysql失败, 请检查安装源是否更新或手动安装！")

            bash('service mysql start')
            bash('mysql -e "create database %s default charset=utf8"' % self.db)
            bash('mysql -e "grant all on %s.* to \'%s\'@\'%s\' identified by \'%s\'"' % (self.db,
                                                                                         self.db_user,
                                                                                         self.db_host,
                                                                                         self.db_pass))

    def _set_env(self):
        color_print('开始关闭防火墙和selinux', 'green')
        if self._is_redhat:
            os.system("export LANG='en_US.UTF-8'")
            if self._is_centos7 or self._is_fedora_new:
                cmd1 = "systemctl status firewalld 2> /dev/null 1> /dev/null"
                cmd2 = "systemctl stop firewalld"
                cmd3 = "systemctl disable firewalld"
                bash('%s && %s && %s' % (cmd1, cmd2, cmd3))
                bash('localectl set-locale LANG=en_US.UTF-8')
                bash('which setenforce 2> /dev/null 1> /dev/null && setenforce 0')
            else:
                bash("sed -i 's/LANG=.*/LANG=en_US.UTF-8/g' /etc/sysconfig/i18n")
                bash('service iptables stop && chkconfig iptables off && setenforce 0')

        if self._is_ubuntu:
            os.system("export LANG='en_US.UTF-8'")
            bash("which iptables && iptables -F")
            bash('which setenforce && setenforce 0')

    def _test_db_conn(self):
        import MySQLdb
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
            if self.mail_port == 465:
                smtp = SMTP_SSL(self.mail_host, port=self.mail_port, timeout=2)
            else:
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

    def _rpm_repo(self):
        if self._is_redhat:
            color_print('开始安装epel源', 'green')
            bash('yum -y install epel-release')

    def _depend_rpm(self):
        color_print('开始安装依赖包', 'green')
        if self._is_redhat:
            cmd = 'yum -y install git python-pip mysql-devel rpm-build gcc automake autoconf python-devel vim sshpass lrzsz readline-devel'
            ret_code = bash(cmd)
            self.check_bash_return(ret_code, "安装依赖失败, 请检查安装源是否更新或手动安装！")
        if self._is_ubuntu:
            cmd = "apt-get -y --force-yes install git python-pip gcc automake autoconf vim sshpass libmysqld-dev python-all-dev lrzsz libreadline-dev"
            ret_code = bash(cmd)
            self.check_bash_return(ret_code, "安装依赖失败, 请检查安装源是否更新或手动安装！")

    def _require_pip(self):
        color_print('开始安装依赖pip包', 'green')
        bash('pip uninstall -y pycrypto')
        bash('rm -rf /usr/lib64/python2.6/site-packages/Crypto/')
        ret_code = bash('pip install -r requirements.txt')
        self.check_bash_return(ret_code, "安装JumpServer 依赖的python库失败！")

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
                db_user = raw_input('请输入数据库服务器用户 [jumpserver]: ').strip()
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
        color_print('请务必先查看wiki https://github.com/jumpserver/jumpserver/wiki')
        time.sleep(3)
        self.check_platform()
        self._rpm_repo()
        self._depend_rpm()
        self._require_pip()
        self._set_env()
        self._input_ip()
        self._input_mysql()
        self._input_smtp()
        self.write_conf()
        os.system('python %s' % os.path.join(jms_dir, 'install/next.py'))


if __name__ == '__main__':
    pre_setup = PreSetup()
    pre_setup.start()
