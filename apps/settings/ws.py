# -*- coding: utf-8 -*-
#

import json

from channels.generic.websocket import JsonWebsocketConsumer

from common.db.utils import close_old_connections
from common.utils import get_logger
from .utils import ping, telnet

logger = get_logger(__name__)


class ToolsWebsocket(JsonWebsocketConsumer):

    def connect(self):
        user = self.scope["user"]
        if user.is_authenticated:
            self.accept()
        else:
            self.close()

    def imitate_ping(self, dest_addr, timeout=3, count=5, psize=64):
        """
        Send `count' ping with `psize' size to `dest_addr' with
        the given `timeout' and display the result.
        """
        logger.info('receive request ping {}'.format(dest_addr))
        self.send_json({'msg': 'Trying {0}...\r\n'.format(dest_addr)})
        for i in range(count):
            msg = 'ping {0} with ...{1}\r\n'
            try:
                delay = ping(dest_addr, timeout, psize)
            except Exception as e:
                msg = msg.format(dest_addr, 'failed. (socket error: {})'.format(str(e)))
                logger.error(msg)
                self.send_json({'msg': msg})
                break
            if delay is None:
                msg = msg.format(dest_addr, 'failed. (timeout within {}sec.)'.format(timeout))
            else:
                delay = delay * 1000
                msg = msg.format(dest_addr, 'get ping in %0.4fms' % delay)
            self.send_json({'msg': msg})

    def imitate_telnet(self, dest_addr, port_num=23, timeout=10):
        logger.info('receive request telnet {}'.format(dest_addr))
        self.send_json({'msg': 'Trying {0} {1}...\r\n'.format(dest_addr, port_num)})
        msg = 'Telnet: {}'
        try:
            is_connective, resp = telnet(dest_addr, port_num, timeout)
            if is_connective:
                msg = msg.format('Connected to {0} {1}\r\n{2}'.format(dest_addr, port_num, resp))
            else:
                msg = msg.format('Connect to {0} {1} {2}\r\nTelnet: Unable to connect to remote host'
                                 .format(dest_addr, port_num, resp))
        except Exception as e:
            logger.error(msg)
            msg = msg.format(str(e))
        finally:
            self.send_json({'msg': msg})

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
