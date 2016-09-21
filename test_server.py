#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 

import socket
import sys
import threading


class ThreadSocket:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))

    def listen(self):
        self.sock.listen(5)
        while True:
            client, address = self.sock.accept()
            client.settimeout(60)
            threading.Thread(target=self.handle_client_request, args=(client, address)).start()

    def handle_client_request(self, client, address):
        print("Get client: %s" % str(address))
        while True:
            try:
                data = client.recv(1024)
                print("sleep : %s" % str(address))
                if data:
                    client.send(data)
                else:
                    raise IndexError('Client has disconnected')
            except:
                client.close()


if __name__ == '__main__':
    server = ThreadSocket('', 9000)
    try:
        server.listen()
    except KeyboardInterrupt:
        sys.exit(1)
