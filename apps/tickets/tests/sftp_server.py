"""A bounded in-process SSH/SFTP peer backed only by a temporary directory."""
import os
import socket
import threading
from contextlib import contextmanager
from pathlib import Path

import paramiko


class Authentication(paramiko.ServerInterface):
    def check_auth_password(self, username, password):
        return paramiko.AUTH_SUCCESSFUL if (username, password) == ('test', 'test') else paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return 'password'

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED if kind == 'session' else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED


class Files(paramiko.SFTPServerInterface):
    def __init__(self, server, *args, root, **kwargs):
        super().__init__(server, *args, **kwargs)
        self.root = Path(root)

    def local(self, path):
        path = self.root / path.lstrip('/')
        if '..' in path.parts:
            raise PermissionError()
        return path

    def stat(self, path):
        try:
            return paramiko.SFTPAttributes.from_stat(self.local(path).stat())
        except OSError as exc:
            return paramiko.SFTPServer.convert_errno(exc.errno)

    def lstat(self, path):
        try:
            return paramiko.SFTPAttributes.from_stat(self.local(path).lstat())
        except OSError as exc:
            return paramiko.SFTPServer.convert_errno(exc.errno)

    def open(self, path, flags, attr):
        try:
            fd = os.open(self.local(path), flags, 0o600)
            file = os.fdopen(fd, 'wb' if flags & (os.O_WRONLY | os.O_RDWR) else 'rb')
            handle = paramiko.SFTPHandle(flags)
            if flags & (os.O_WRONLY | os.O_RDWR):
                handle.writefile = file
            else:
                handle.readfile = file
            handle.stat = lambda: paramiko.SFTPAttributes.from_stat(os.fstat(file.fileno()))
            return handle
        except OSError as exc:
            return paramiko.SFTPServer.convert_errno(exc.errno)

    def chattr(self, path, attr):
        paramiko.SFTPServer.set_file_attr(str(self.local(path)), attr)
        return paramiko.SFTP_OK

    def rename(self, old, new):
        if self.local(new).exists():
            return paramiko.SFTP_FAILURE
        os.rename(self.local(old), self.local(new))
        return paramiko.SFTP_OK

    def remove(self, path):
        try:
            self.local(path).unlink()
            return paramiko.SFTP_OK
        except OSError as exc:
            return paramiko.SFTPServer.convert_errno(exc.errno)


@contextmanager
def serve(root):
    client_socket, server_socket = socket.socketpair()
    server = paramiko.Transport(server_socket)
    server.add_server_key(paramiko.RSAKey.generate(2048))
    server.set_subsystem_handler('sftp', paramiko.SFTPServer, Files, root=root)
    thread = threading.Thread(target=server.start_server, kwargs={'server': Authentication()}, daemon=True)
    thread.start()
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect('localhost', sock=client_socket, username='test', password='test',
                       look_for_keys=False, allow_agent=False, timeout=3, banner_timeout=3, auth_timeout=3)
        with client.open_sftp() as sftp:
            sftp.get_channel().settimeout(3)
            yield sftp
    finally:
        client.close()
        server.close()
        client_socket.close()
        server_socket.close()
        thread.join(timeout=3)
