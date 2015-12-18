#!/usr/bin/python
# coding: utf-8

import sys
import os
import django
from django.core.management import execute_from_command_line
import shutil

jms_dir = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))
sys.path.append(jms_dir)

os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings'
if django.get_version() != '1.6':
    setup = django.setup()

from juser.user_api import db_add_user, server_add_user
from connect import color_print


class Setup(object):
    """
    安装jumpserver向导
    """

    def __init__(self):
        self.admin_user = ''
        self.admin_pass = ''

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

    @staticmethod
    def _cp_zzsh():
        os.chdir(jms_dir)
        shutil.copy('zzjumpserver.sh', '/etc/profile.d/')

    def start(self):
        print "开始安装Jumpserver, 要求环境为 CentOS 6.5 x86_64"
        self._sync_db()
        self._create_admin()


if __name__ == '__main__':
    setup = Setup()
    setup.start()
