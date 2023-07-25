# -*- coding: utf-8 -*-
#

import json

from channels.generic.websocket import JsonWebsocketConsumer

from common.db.utils import close_old_connections
from common.utils import get_logger
from .utils import verbose_ping, verbose_telnet, verbose_nmap

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

    def imitate_ping(self, dest_ip, timeout=3, count=5, psize=64):
        """
        Send `count' ping with `psize' size to `dest_ip' with
        the given `timeout' and display the result.
        """
        logger.info('receive request ping {}'.format(dest_ip))
        verbose_ping(dest_ip, timeout, count, psize, display=self.send_msg)

    def imitate_telnet(self, dest_ip, dest_port=23, timeout=10):
        logger.info('receive request telnet {}'.format(dest_ip))
        verbose_telnet(dest_ip, dest_port, timeout, display=self.send_msg)

    def imitate_nmap(self, dest_ip, dest_port=None, timeout=None):
        logger.info('receive request nmap {}'.format(dest_ip))
        verbose_nmap(dest_ip, dest_port, timeout, display=self.send_msg)

    def receive(self, text_data=None, bytes_data=None, **kwargs):
        data = json.loads(text_data)
        tool_type = data.pop('tool_type', 'Ping')

        tool_func = getattr(self, f'imitate_{tool_type.lower()}')
        tool_func(**data)
        self.close()

    def disconnect(self, code):
        self.close()
        close_old_connections()
