#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 


import base64
from binascii import hexlify
import os
import sys
import threading
import traceback
import tty
import termios
import struct, fcntl, signal, socket, select
import errno

import paramiko
from paramiko.py3compat import b, u, decodebytes


paramiko.util.log_to_file('demo_server.log')

host_key = paramiko.RSAKey(filename='test_rsa.key')


class SSHService(paramiko.ServerInterface):
    # 'data' is the output of base64.encodestring(str(key))
    # (using the "user_rsa_key" files)
    data = (b'AAAAB3NzaC1yc2EAAAABIwAAAIEAyO4it3fHlmGZWJaGrfeHOVY7RWO3P9M7hp'
            b'fAu7jJ2d7eothvfeuoRFtJwhUmZDluRdFyhFY/hFAh76PJKGAusIqIQKlkJxMC'
            b'KDqIexkgHAfID/6mqvmnSJf0b5W8v5h2pI/stOSwTQ+pxVhwJ9ctYDhRSlF0iT'
            b'UWT10hcuO4Ks8=')
    good_pub_key = paramiko.RSAKey(data=decodebytes(data))

    def __init__(self):
        self.event = threading.Event()

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        print(username, password)
        if (username == 'robey') and (password == 'foo'):
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_auth_publickey(self, username, key):
        print('Auth attempt with key: ' + u(hexlify(key.get_fingerprint())))
        if (username == 'robey') and (key == self.good_pub_key):
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return 'password,publickey'

    def check_channel_shell_request(self, channel):
        self.event.set()
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth,
                                     pixelheight, modes):
        return True


class SSHServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.server_ssh = None
        self.server_chan = None

    def connect(self):
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname='127.0.0.1', port=22, username='root', password='redhat')
        self.server_ssh = ssh
        self.server_chan = channel = ssh.invoke_shell(term='xterm')
        return channel

    def handle_ssh_request(self, client, addr):
        print('Got a connection!')
        try:
            t = paramiko.Transport(client, gss_kex=False)
            t.set_gss_host(socket.getfqdn(""))
            try:
                t.load_server_moduli()
            except:
                print('(Failed to load moduli -- gex will be unsupported.)')
                raise
            t.add_server_key(host_key)
            service = SSHService()
            try:
                t.start_server(server=service)
            except paramiko.SSHException:
                print('*** SSH negotiation failed.')
                return

            chan = t.accept(20)

            if chan is None:
                print('*** No channel.')
                return
            print('Authenticated!')

            chan.settimeout(100)

            chan.send('\r\n\r\nWelcome to my dorky little BBS!\r\n\r\n')
            chan.send('We are on fire all the time!  Hooray!  Candy corn for everyone!\r\n')
            chan.send('Happy birthday to Robot Dave!\r\n\r\n')
            server_chan = self.connect()
            if not service.event.is_set():
                print('*** Client never asked for a shell.')
                return
            server_data = []
            input_mode = True
            while True:
                r, w, e = select.select([server_chan, chan], [], [])


                if chan in r:
                    recv_data = chan.recv(1024).decode('utf8')
                    # print("From client: " + repr(recv_data))
                    if len(recv_data) == 0:
                        break
                    server_chan.send(recv_data)

                if server_chan in r:
                    recv_data = server_chan.recv(1024).decode('utf8')
                    # print("From server: " + repr(recv_data))
                    if len(recv_data) == 0:
                        break
                    chan.send(recv_data)
                    if len(recv_data) > 20:
                        server_data.append('...')
                    else:
                        server_data.append(recv_data)
                    try:
                        if repr(server_data[-2]) == u'\r\n':
                            result = server_data.pop()
                            server_data.pop()
                            command = ''.join(server_data)
                            server_data = []
                            print(">>> Command: %s" % command)
                            print(result)
                    except IndexError:
                        pass
                print(server_data)


        except Exception as e:
            print('*** Caught exception: ' + str(e.__class__) + ': ' + str(e))
            traceback.print_exc()
            try:
                t.close()
            except:
                pass
            sys.exit(1)

    def listen(self):
        self.sock.listen(5)
        while True:
            try:
                client, addr = self.sock.accept()
                print('Listening for connection ...')
                threading.Thread(target=self.handle_ssh_request, args=( client, addr)).start()
            except Exception as e:
                print('*** Bind failed: ' + str(e))
                traceback.print_exc()
                sys.exit(1)


if __name__ == '__main__':
    server = SSHServer('', 2200)
    try:
        server.listen()
    except KeyboardInterrupt:
        sys.exit(1)

