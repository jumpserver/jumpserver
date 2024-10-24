# -*- coding: utf-8 -*-
import os
import io
import paramiko
from jms_storage.base import ObjectStorage


class SFTPStorage(ObjectStorage):

    def __init__(self, config):
        self.sftp = None
        self.sftp_host = config.get('SFTP_HOST', None)
        self.sftp_port = int(config.get('SFTP_PORT', 22))
        self.sftp_username = config.get('SFTP_USERNAME', '')
        self.sftp_secret_type = config.get('STP_SECRET_TYPE', 'password')
        self.sftp_password = config.get('SFTP_PASSWORD', '')
        self.sftp_private_key = config.get('STP_PRIVATE_KEY', '')
        self.sftp_passphrase = config.get('STP_PASSPHRASE', '')
        self.sftp_root_path = config.get('SFTP_ROOT_PATH', '/tmp')
        self.ssh = paramiko.SSHClient()
        self.connect()

    def connect(self):
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if self.sftp_secret_type == 'password':
            self.ssh.connect(self.sftp_host, self.sftp_port, self.sftp_username, self.sftp_password)
        elif self.sftp_secret_type == 'ssh_key':
            pkey = paramiko.RSAKey.from_private_key(io.StringIO(self.sftp_private_key))
            self.ssh.connect(self.sftp_host, self.sftp_port, self.sftp_username, pkey=pkey,
                             passphrase=self.sftp_passphrase)
        self.sftp = self.ssh.open_sftp()

    def confirm_connected(self):
        try:
            self.sftp.getcwd()
        except Exception as e:
            self.connect()

    def upload(self, src, target):
        local_file = src
        remote_file = os.path.join(self.sftp_root_path, target)
        try:
            self.confirm_connected()
            mode = os.stat(local_file).st_mode
            remote_dir = os.path.dirname(remote_file)
            if not self.exists(remote_dir):
                self.sftp.mkdir(remote_dir)
            self.sftp.put(local_file, remote_file)
            self.sftp.chmod(remote_file, mode)
            return True, None
        except Exception as e:
            return False, e

    def download(self, src, target):
        remote_file = src
        local_file = target
        self.confirm_connected()
        try:
            local_dir = os.path.dirname(local_file)
            if not os.path.exists(local_dir):
                os.makedirs(local_dir)
            mode = self.sftp.stat(remote_file).st_mode
            self.sftp.get(remote_file, local_file)
            os.chmod(local_file, mode)
            return True, None
        except Exception as e:
            return False, e

    def delete(self, path):
        path = os.path.join(self.sftp_root_path, path)
        self.confirm_connected()
        if not self.exists(path):
            raise FileNotFoundError('File not exist error(%s)' % path)
        try:
            self.sftp.remove(path)
            return True, None
        except Exception as e:
            return False, e

    def check_dir_exist(self, d):
        self.confirm_connected()
        try:
            self.sftp.stat(d)
            return True
        except Exception:
            return False

    def mkdir(self, dirs):
        self.confirm_connected()
        try:
            if not self.exists(dirs):
                self.sftp.mkdir(dirs)
            return True, None
        except Exception as e:
            return False, e

    def exists(self, target):
        self.confirm_connected()
        try:
            self.sftp.stat(target)
            return True
        except:
            return False

    def close(self):
        self.sftp.close()
        self.ssh.close()
