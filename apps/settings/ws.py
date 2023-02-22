# -*- coding: utf-8 -*-
#

import json

from channels.generic.websocket import JsonWebsocketConsumer

from common.db.utils import close_old_connections
from common.utils import get_logger
from .utils import verbose_ping, verbose_telnet

logger = get_logger(__name__)


class ToolsWebsocket(JsonWebsocketConsumer):

    def connect(self):
        user = self.scope["user"]
        if user.is_authenticated:
            self.accept()
        else:
            self.close()

    def send_msg(self, msg):
        self.send_json({'msg': msg + '\r\n'})

    def imitate_ping(self, dest_addr, timeout=3, count=5, psize=64):
        """
        Send `count' ping with `psize' size to `dest_addr' with
        the given `timeout' and display the result.
        """
        logger.info('receive request ping {}'.format(dest_addr))
        verbose_ping(dest_addr, timeout, count, psize, display=self.send_msg)

    def imitate_telnet(self, dest_addr, port_num=23, timeout=10):
        logger.info('receive request telnet {}'.format(dest_addr))
        verbose_telnet(dest_addr, port_num, timeout, display=self.send_msg)

    def receive(self, text_data=None, bytes_data=None, **kwargs):
        data = json.loads(text_data)
        tool_type = data.get('tool_type', 'Ping')
        dest_addr = data.get('dest_addr')
        if tool_type == 'Ping':
            self.imitate_ping(dest_addr)
        else:
            port_num = data.get('port_num')
            self.imitate_telnet(dest_addr, port_num)
        self.close()

    def disconnect(self, code):
        self.close()
        close_old_connections()
