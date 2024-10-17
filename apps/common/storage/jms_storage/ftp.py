# -*- coding: utf-8 -*-
#

import os
from ftplib import FTP, error_perm
from .base import ObjectStorage


class FTPStorage(ObjectStorage):

    def __init__(self, config):
        self.host = config.get("HOST", None)
        self.port = int(config.get("PORT", 21))
        self.username = config.get("USERNAME", None)
        self.password = config.get("PASSWORD", None)
        self.pasv = bool(config.get("PASV", False))
        self.dir = config.get("DIR", "replay")
        self.client = FTP()
        self.client.encoding = 'utf-8'
        self.client.set_pasv(self.pasv)
        self.pwd = '.'
        self.connect()

    def connect(self, timeout=-999, source_address=None):
        self.client.connect(self.host, self.port, timeout, source_address)
        self.client.login(self.username, self.password)
        if not self.check_dir_exist(self.dir):
            self.mkdir(self.dir)
        self.client.cwd(self.dir)
        self.pwd = self.client.pwd()

    def confirm_connected(self):
        try:
            self.client.pwd()
        except Exception:
            self.connect()

    def upload(self, src, target):
        self.confirm_connected()
        target_dir = os.path.dirname(target)
        exist = self.check_dir_exist(target_dir)
        if not exist:
            ok = self.mkdir(target_dir)
            if not ok:
                raise PermissionError('Dir create error: %s' % target)
        try:
            with open(src, 'rb') as f:
                self.client.storbinary('STOR '+target, f)
            return True, None
        except Exception as e:
            return False, e

    def download(self, src, target):
        self.confirm_connected()
        try:
            os.makedirs(os.path.dirname(target), 0o755, exist_ok=True)
            with open(target, 'wb') as f:
                self.client.retrbinary('RETR ' + src, f.write)
            return True, None
        except Exception as e:
            return False, e

    def delete(self, path):
        self.confirm_connected()
        if not self.exists(path):
            raise FileNotFoundError('File not exist error(%s)' % path)
        try:
            self.client.delete(path)
            return True, None
        except Exception as e:
            return False, e

    def check_dir_exist(self, d):
        pwd = self.client.pwd()
        try:
            self.client.cwd(d)
            self.client.cwd(pwd)
            return True
        except error_perm:
            return False

    def mkdir(self, dirs):
        self.confirm_connected()
        # 创建多级目录，ftplib不支持一次创建多级目录
        dir_list = dirs.split('/')
        pwd = self.client.pwd()
        try:
            for d in dir_list:
                if not d or d in ['.']:
                    continue
                # 尝试切换目录
                try:
                    self.client.cwd(d)
                    continue
                except:
                    pass
                # 切换失败创建这个目录，再切换
                try:
                    self.client.mkd(d)
                    self.client.cwd(d)
                except:
                    return False
            return True
        finally:
            self.client.cwd(pwd)

    def exists(self, target):
        self.confirm_connected()
        try:
            self.client.size(target)
            return True
        except:
            return False

    def close(self):
        self.client.close()
