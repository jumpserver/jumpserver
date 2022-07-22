# -*- coding: utf-8 -*-
#

import json
import socket

from channels.generic.websocket import JsonWebsocketConsumer

from .utils import ping, telnet
from common.utils import get_logger

logger = get_logger(__name__)


class PingMsgWebsocket(JsonWebsocketConsumer):

    def connect(self):
        user = self.scope["user"]
        if user.is_authenticated:
            self.accept()
        else:
            self.close()

    def imitate_ping(self, dest_addr, timeout=2, count=5, psize=64):
        """
        Send `count' ping with `psize' size to `dest_addr' with
        the given `timeout' and display the result.
        """
        logger.debug('receive request ping %s' % dest_addr)
        for i in range(count):
            msg = 'ping %s with ...' % dest_addr
            try:
                delay = ping(dest_addr, timeout, psize)
            except Exception as e:
                msg += 'failed. (socket error: %s)' % str(e)
                self.send_json({'ping': msg})
                break
            if delay is None:
                msg += 'failed. (timeout within %ssec.)' % timeout
            else:
                delay = delay * 1000
                msg += 'get ping in %0.4fms' % delay
            self.send_json({'ping': msg})
        self.close()

    def receive(self, text_data=None, bytes_data=None, **kwargs):
        data = json.loads(text_data)
        destination_ip = data.get('destination_ip')
        self.imitate_ping(destination_ip)


class TelnetMsgWebsocket(JsonWebsocketConsumer):

    def connect(self):
        user = self.scope["user"]
        if user.is_authenticated:
            self.accept()
        else:
            self.close()

    def imitate_telnet(self, dest_addr, port_number=23, timeout=10):
        logger.debug('receive request telnet %s' % dest_addr)
        self.send_json({'telnet': 'Trying {0} {1}...'.format(dest_addr, port_number)})
        try:
            is_connective, msg = telnet(dest_addr, port_number, timeout)
            if is_connective:
                self.send_json({'telnet': 'Telnet: Connected to {0} {1}\n{2}'.format(dest_addr, port_number, msg)})
            else:
                self.send_json({'telnet': 'Telnet: Connect to {0} {1} : {2}'.format(dest_addr, port_number, msg)})
                self.send_json({'telnet': 'Telnet: Unable to connect to remote host'})
        except Exception as e:
            self.send_json({'telnet': 'Telnet: {0}'.format(str(e))})
        self.close()

    def receive(self, text_data=None, bytes_data=None, **kwargs):
        data = json.loads(text_data)
        destination_ip = data.get('destination_ip')
        port_number = data.get('port_number')
        self.imitate_telnet(destination_ip, port_number)
