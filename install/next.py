#!/usr/bin/python
# coding: utf-8

import sys
import os
import django
from django.core.management import execute_from_command_line
import shutil
import urllib
import socket

jms_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(jms_dir)

os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings'
if django.get_version() != '1.6':
    setup = django.setup()

from juser.user_api import db_add_user, get_object, User
from install import color_print
from jumpserver.api import get_mac_address

socket.setdefaulttimeout(2)


class Setup(object):
    """
    安装jumpserver向导
    """

    def __init__(self):
        self.admin_user = 'admin'
        self.admin_pass = '5Lov@wife'

    @staticmethod
    def _pull():
        color_print('开始更新jumpserver', 'green')
        # bash('git pull')
        try:
            mac = get_mac_address()
            version = urllib.urlopen('http://jumpserver.org/version/?id=%s' % mac)
        except:
            pass
        os.chdir(jms_dir)
        os.chmod('logs', 0777)
        os.chmod('keys', 0777)

    def _input_admin(self):
        while True:
            print
            admin_user = raw_input('请输入管理员用户名 [%s]: ' % self.admin_user).strip()
            admin_pass = raw_input('请输入管理员密码: [%s]: ' % self.admin_pass).strip()
            admin_pass_again = raw_input('请再次输入管理员密码: [%s]: ' % self.admin_pass).strip()

            if admin_user:
                self.admin_user = admin_user

            if not admin_pass_again:
                admin_pass_again = self.admin_pass

            if admin_pass:
                self.admin_pass = admin_pass

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
        user = get_object(User, username=self.admin_user)
        if user:
            user.delete()
        db_add_user(username=self.admin_user, password=self.admin_pass, role='SU', name='admin', groups='',
                    admin_groups='', email='admin@jumpserver.org', uuid='MayBeYouAreTheFirstUser', is_active=True)
        os.system('id %s &> /dev/null || useradd %s' % (self.admin_user, self.admin_user))

    @staticmethod
    def _cp_zzsh():
        os.chdir(os.path.join(jms_dir, 'install'))
        shutil.copy('zzjumpserver.sh', '/etc/profile.d/')

    @staticmethod
    def _run_service():
        os.system('sh %s start' % os.path.join(jms_dir, 'service.sh'))
        print
        color_print('安装成功，请访问web, 祝你使用愉快。请访问 https://github.com/ibuler/jumpserver 查看文档', 'green')

    def start(self):
        print "开始安装Jumpserver, 要求环境为 CentOS 6.5 x86_64"
        self._pull()
        self._sync_db()
        self._input_admin()
        self._create_admin()
        self._cp_zzsh()
        self._run_service()


if __name__ == '__main__':
    setup = Setup()
    setup.start()
