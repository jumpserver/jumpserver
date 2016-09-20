#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 


import base64
from binascii import hexlify
import os
import socket
import sys
import threading
import traceback

import paramiko
from paramiko.py3compat import b, u, decodebytes


paramiko.util.log_to_file('demo_server.log')

host_key = paramiko.RSAKey(filename='test_rsa.key')


class Server(paramiko.ServerInterface):
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


def handle_ssh_request(client, addr):
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
        server = Server()
        try:
            t.start_server(server=server)
        except paramiko.SSHException:
            print('*** SSH negotiation failed.')
            return

        while True:
            # wait for auth
            chan = t.accept(20)
            if chan is None:
                print('*** No channel.')
                return
            print('Authenticated!')

            server.event.wait(10)
            if not server.event.is_set():
                print('*** Client never asked for a shell.')
                return

            chan.send('\r\n\r\nWelcome to my dorky little BBS!\r\n\r\n')
            chan.send('We are on fire all the time!  Hooray!  Candy corn for everyone!\r\n')
            chan.send('Happy birthday to Robot Dave!\r\n\r\n')
            chan.send('Username: ')
            f = chan.makefile('rU')
            username = f.readline().strip('\r\n')
            chan.send('\r\nI don\'t like you, ' + username + '.\r\n')
            chan.close()

    except Exception as e:
        print('*** Caught exception: ' + str(e.__class__) + ': ' + str(e))
        traceback.print_exc()
        try:
            t.close()
        except:
            pass
        sys.exit(1)


def run_server():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(('', 2200))
    except Exception as e:
        print('*** Bind failed: ' + str(e))
        traceback.print_exc()
        sys.exit(1)

    try:
        sock.listen(100)
        print('Listening for connection ...')
        client, addr = sock.accept()

        t = threading.Thread(target=handle_ssh_request, args=(client, addr))
        t.start()

    except Exception as e:
        print('*** Listen/accept failed: ' + str(e))
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    run_server()