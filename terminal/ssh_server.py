#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
import sys
import os
import base64
from binascii import hexlify
import sys
import threading
from multiprocessing import process
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
from paramiko.py3compat import b, u, decodebytes

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
from utils import get_logger


logger = get_logger(__name__)


class SSHServerInterface(paramiko.ServerInterface):
    host_key_path = os.path.join(BASE_DIR, 'host_rsa_key')
    channel_pools = []

    def __init__(self, client, addr):
        self.event = threading.Event()
        self.client = client
        self.addr = addr
        self.user = None

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
        self.user = check_user_is_valid(username=username, password=password)
        if self.user:
            logger.info('Accepted password for %(user)s from %(host)s port %(port)s ' % {
                'user': username,
                'host': self.addr[0],
                'port': self.addr[1],
            })
            return paramiko.AUTH_SUCCESSFUL
        else:
            logger.info('Authentication password failed for %(user)s from %(host)s port %(port)s ' % {
                'user': username,
                'host': self.addr[0],
                'port': self.addr[1],
            })
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, public_key):
        self.user = check_user_is_valid(username=username, public_key=public_key)
        if self.user:
            logger.info('Accepted public key for %(user)s from %(host)s port %(port)s ' % {
                'user': username,
                'host': self.addr[0],
                'port': self.addr[1],
            })
            return paramiko.AUTH_SUCCESSFUL
        else:
            logger.info('Authentication public key failed for %(user)s from %(host)s port %(port)s ' % {
                'user': username,
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
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth,
                                     pixelheight, modes):
        return True

    def check_channel_window_change_request(self, channel, width, height, pixelwidth, pixelheight):
        logger.info('Change window size %s * %s' % (width, height))
        logger.info('Change length %s ' % len(self.__class__.channel_pools))
        for channel in self.__class__.channel_pools:
            channel.send("Hello world")
        return True


class SSHServer:
    def __init__(self, host='127.0.0.1', port=2200):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.server_ssh = None
        self.server_channel = None
        self.client_channel = None

    def connect(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname='127.0.0.1', port=22, username='root', password='redhat')
        self.server_ssh = ssh
        self.server_channel = channel = ssh.invoke_shell(term='xterm')
        return channel

    def handle_ssh_request(self, client, addr):
        logger.info("Get connection from %(host)s:%(port)s" % {
            'host': addr[0],
            'port': addr[1],
        })
        try:
            transport = paramiko.Transport(client, gss_kex=False)
            transport.set_gss_host(socket.getfqdn(""))
            try:
                transport.load_server_moduli()
            except:
                logger.warning('(Failed to load moduli -- gex will be unsupported.)')
                raise

            transport.add_server_key(SSHServerInterface.get_host_key())
            ssh_interface = SSHServerInterface(client, addr)
            try:
                transport.start_server(server=ssh_interface)
            except paramiko.SSHException:
                print('*** SSH negotiation failed.')
                return

            self.client_channel = client_channel = transport.accept(20)
            if client_channel is None:
                print('*** No channel.')
                return
            print('Authenticated!')

            client_channel.settimeout(100)

            client_channel.send('\r\n\r\nWelcome to my dorky little BBS!\r\n\r\n')
            client_channel.send('We are on fire all the time!  Hooray!  Candy corn for everyone!\r\n')
            client_channel.send('Happy birthday to Robot Dave!\r\n\r\n')
            server_channel = self.connect()
            if not ssh_interface.event.is_set():
                print('*** Client never asked for a shell.')
                return

            while True:
                r, w, x = select.select([client_channel, server_channel], [], [])

                if client_channel in r:
                    data_client = client_channel.recv(1024)
                    logger.info(data_client)
                    if len(data_client) == 0:
                        break
                    # client_channel.send(data_client)
                    server_channel.send(data_client)

                if server_channel in r:
                    data_server = server_channel.recv(1024)
                    if len(data_server) == 0:
                        break
                    client_channel.send(data_server)

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

        except Exception:
            client_channel.close()
            server_channel.close()
            logger.info('Close with server %s from %s' % ('127.0.0.1', '127.0.0.1'))

    def listen(self):
        self.sock.listen(5)
        print('Start ssh server %(host)s:%(port)s' % {'host': self.host, 'port': self.port})
        while True:
            try:
                client, addr = self.sock.accept()
                print('Listening for connection ...')
                # t = threading.Thread(target=self.handle_ssh_request, args=(client, addr))
                t = process.Process(target=self.handle_ssh_request, args=(client, addr))

                t.daemon = True
                t.start()
            except Exception as e:
                print('*** Bind failed: ' + str(e))
                traceback.print_exc()
                sys.exit(1)


if __name__ == '__main__':
    server = SSHServer(host='', port=2200)
    try:
        server.listen()
    except KeyboardInterrupt:
        sys.exit(1)

