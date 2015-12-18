#!/usr/bin/python
# coding: utf-8

import subprocess
import time
import os
import sys


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


class PreSetup(object):

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

    def start(self):
        self._rpm_repo()
        self._depend_rpm()
        self._require_pip()
        os.system('python next.py')


if __name__ == '__main__':
    pre_setup = PreSetup()
    pre_setup.start()
