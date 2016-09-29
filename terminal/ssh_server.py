#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

__version__ = '0.3.3'

import sys
import os
import base64
import time
from binascii import hexlify
import sys
import threading
from multiprocessing.process import Process
import traceback
import tty
import termios
import struct
import fcntl
import signal
import socket
import select
import errno
import paramiko
import django

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
APP_DIR = os.path.join(os.path.dirname(BASE_DIR), 'apps')
sys.path.append(APP_DIR)
os.environ['DJANGO_SETTINGS_MODULE'] = 'jumpserver.settings'

try:
    django.setup()
except IndexError:
    pass

from django.conf import settings
from users.utils import ssh_key_gen, check_user_is_valid
from utils import get_logger, SSHServerException, control_char


logger = get_logger(__name__)

paramiko.util.log_to_file(os.path.join(BASE_DIR, 'logs', 'paramiko.log'))


class SSHServer(paramiko.ServerInterface):
    host_key_path = os.path.join(BASE_DIR, 'host_rsa_key')
    channel_pools = []

    def __init__(self, client, addr):
        self.event = threading.Event()
        self.change_window_size_event = threading.Event()
        self.client = client
        self.addr = addr
        self.username = None
        self.user = None
        self.channel_width = None
        self.channel_height = None

    @classmethod
    def host_key(cls):
        return cls.get_host_key()

    @classmethod
    def get_host_key(cls):
        logger.debug("Get ssh server host key")
        if not os.path.isfile(cls.host_key_path):
            cls.host_key_gen()
        return paramiko.RSAKey(filename=cls.host_key_path)

    @classmethod
    def host_key_gen(cls):
        logger.debug("Generate ssh server host key")
        ssh_key, ssh_pub_key = ssh_key_gen()
        with open(cls.host_key_path, 'w') as f:
            f.write(ssh_key)

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        self.user = user = check_user_is_valid(username=username, password=password)
        if self.user:
            self.username = username = user.username
            logger.info('Accepted password for %(username)s from %(host)s port %(port)s ' % {
                'username': username,
                'host': self.addr[0],
                'port': self.addr[1],
            })
            return paramiko.AUTH_SUCCESSFUL
        else:
            logger.info('Authentication password failed for %(username)s from %(host)s port %(port)s ' % {
                'username': username,
                'host': self.addr[0],
                'port': self.addr[1],
            })
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, public_key):
        self.user = user = check_user_is_valid(username=username, public_key=public_key)

        if self.user:
            self.username = username = user.username
            logger.info('Accepted public key for %(username)s from %(host)s port %(port)s ' % {
                'username': username,
                'host': self.addr[0],
                'port': self.addr[1],
            })
            return paramiko.AUTH_SUCCESSFUL
        else:
            logger.info('Authentication public key failed for %(username)s from %(host)s port %(port)s ' % {
                'username': username,
                'host': self.addr[0],
                'port': self.addr[1],
            })
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        auth_method_list = []
        if settings.CONFIG.SSH_PASSWORD_AUTH:
            auth_method_list.append('password')
        if settings.CONFIG.SSH_PUBLICK_KEY_AUTH:
            auth_method_list.append('publickey')
        return ','.join(auth_method_list)

    def check_channel_shell_request(self, channel):
        self.event.set()
        self.__class__.channel_pools.append(channel)
        channel.username = self.username
        channel.addr = self.addr
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth,
                                     pixelheight, modes):
        channel.change_window_size_event = threading.Event()
        channel.width = width
        channel.height = height
        return True

    def check_channel_window_change_request(self, channel, width, height, pixelwidth, pixelheight):
        channel.change_window_size_event.set()
        channel.width = width
        channel.height = height
        return True


class BackendServer:
    def __init__(self, host, port, username):
        self.host = host
        self.port = port
        self.username = username
        self.ssh = None
        self.channel = None

    def connect(self, term='xterm', width=80, height=24, timeout=10):
        self.ssh = ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            ssh.connect(hostname=self.host, port=self.port, username=self.username, password=self.host_password,
                        pkey=self.host_private_key, look_for_keys=False, allow_agent=True, compress=True, timeout=timeout)
        except Exception:
            logger.warning('Connect backend server %s failed' % self.host)
            return None

        self.channel = channel = ssh.invoke_shell(term=term, width=width, height=height)
        logger.info('Connect backend server %(username)s@%(host)s:%(port)s successfully' % {
            'username': self.username,
            'host': self.host,
            'port': self.port,
        })
        channel.settimeout(100)
        channel.host = self.host
        channel.port = self.port
        channel.username = self.username
        return channel

    @property
    def host_password(self):
        return 'redhat'

    @property
    def host_private_key(self):
        return None


class Navigation:
    def __init__(self, username, client_channel):
        self.username = username
        self.client_channel = client_channel

    def display_banner(self):
        client_channel = self.client_channel
        client_channel.send(control_char.clear)
        client_channel.send('\r\n\r\n\t\tWelcome to use Jumpserver open source system !\r\n\r\n')
        client_channel.send('If you find some bug please contact us <ibuler@qq.com>\r\n')
        client_channel.send('See more at https://www.jumpserver.org\r\n')
        # client_channel.send(self.username)

    def display(self):
        self.display_banner()

    def return_to_connect(self):
        pass


class JumpServer:
    backend_server_pools = []
    backend_channel_pools = []
    client_channel_pools = []

    CONTROL_CHAR = {
        'clear': ''
    }

    def __init__(self):
        self.listen_host = '0.0.0.0'
        self.listen_port = 2222

    def display_navigation(self, username, client_channel):
        nav = Navigation(username, client_channel)
        nav.display()
        return '127.0.0.1', 22, 'root'

    def get_client_channel(self, client, addr):
        transport = paramiko.Transport(client, gss_kex=False)
        transport.set_gss_host(socket.getfqdn(""))
        try:
            transport.load_server_moduli()
        except:
            logger.warning('Failed to load moduli -- gex will be unsupported.')
            raise

        transport.add_server_key(SSHServer.get_host_key())
        ssh_server = SSHServer(client, addr)

        try:
            transport.start_server(server=ssh_server)
        except paramiko.SSHException:
            logger.warning('SSH negotiation failed.')

        client_channel = transport.accept(20)
        if client_channel is None:
            logger.warning('No ssh channel get.')
            return None

        self.__class__.client_channel_pools.append(client_channel)
        if not ssh_server.event.is_set():
            logger.warning('Client never asked for a shell.')
        return client_channel

    def get_backend_channel(self, host, port, username, term='xterm', width=80, height=24):
        backend_server = BackendServer(host, port, username)
        backend_channel = backend_server.connect(term=term, width=width, height=height)

        if backend_channel is None:
            logger.warning('Connect %(username)s@%(host)s:%(port)s failed' % {
                'username': username,
                'host': host,
                'port': port,
            })
            return None

        self.__class__.backend_server_pools.append(backend_server)
        self.__class__.backend_channel_pools.append(backend_channel)

        return backend_channel

    def handle_ssh_request(self, client, addr):
        logger.info("Get ssh request from %(host)s:%(port)s" % {
            'host': addr[0],
            'port': addr[1],
        })

        try:
            client_channel = self.get_client_channel(client, addr)
            if client_channel is None:
                client.close()
                return

            host, port, username = self.display_navigation('root', client_channel)
            backend_channel = self.get_backend_channel(host, port, username,
                                                       width=client_channel.width,
                                                       height=client_channel.height)
            if backend_channel is None:
                client.shutdown()
                client.close()
                client.send('Close')
                print(client)
                print(dir(client))
                return

            while True:
                r, w, x = select.select([client_channel, backend_channel], [], [])

                if client_channel.change_window_size_event.is_set():
                    backend_channel.resize_pty(width=client_channel.width, height=client_channel.height)

                if client_channel in r:
                    client_data = client_channel.recv(1024)
                    if len(client_data) == 0:
                        logger.info('Logout from ssh server %(host)s: %(username)s' % {
                            'host': addr[0],
                            'username': client_channel.username,
                        })
                        break
                    print('CC: ' + repr(client_data))
                    backend_channel.send(client_data)

                if backend_channel in r:
                    backend_data = backend_channel.recv(1024)
                    if len(backend_data) == 0:
                        client_channel.send('Disconnect from %s \r\n' % backend_channel.host)
                        client_channel.close()
                        logger.info('Logout from backend server %(host)s: %(username)s' % {
                            'host': backend_channel.host,
                            'username': backend_channel.username,
                        })
                        break
                    print('SS: ' + repr(backend_data))
                    client_channel.send(backend_data)

                    # if len(recv_data) > 20:
                    #     server_data.append('...')
                    # else:
                    #     server_data.append(recv_data)
                #     try:
                #         if repr(server_data[-2]) == u'\r\n':
                #             result = server_data.pop()
                #             server_data.pop()
                #             command = ''.join(server_data)
                #             server_data = []
                #     except IndexError:
                #         pass

        # Todo: catch other exception
        except IndexError:
            logger.info('Close with server %s from %s' % (addr[0], addr[1]))
            sys.exit(100)

    def listen(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.listen_host, self.listen_port))
        sock.listen(5)

        print(time.ctime())
        print('Jumpserver version %s, more see https://www.jumpserver.org' % __version__)
        print('Starting ssh server at %(host)s:%(port)s' % {'host': self.listen_host, 'port': self.listen_port})
        print('Quit the server with CONTROL-C.')

        while True:
            try:
                client, addr = sock.accept()
                thread = threading.Thread(target=self.handle_ssh_request, args=(client, addr))
                thread.daemon = True
                thread.start()
            except Exception as e:
                logger.error('Bind failed: ' + str(e))
                traceback.print_exc()
                sys.exit(1)


if __name__ == '__main__':
    server = JumpServer()
    try:
        server.listen()
    except KeyboardInterrupt:
        sys.exit(1)

