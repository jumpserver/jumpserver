# -*- coding: utf-8 -*-
#
import json

from channels.generic.websocket import AsyncJsonWebsocketConsumer

from common.db.utils import close_old_connections
from common.utils import get_logger
from .tools import verbose_ping, verbose_telnet, verbose_nmap, verbose_tcpdump


logger = get_logger(__name__)


class ToolsWebsocket(AsyncJsonWebsocketConsumer):

    async def connect(self):
        user = self.scope["user"]
        if user.is_authenticated:
            await self.accept()
        else:
            await self.close()

    async def send_msg(self, msg=''):
        await self.send_json({'msg': msg + '\r\n'})

    async def imitate_ping(self, dest_ip, timeout=3, count=5, psize=64):
        params = {
            'dest_ip': dest_ip, 'timeout': timeout,
            'count': count, 'psize': psize
        }
        logger.info(f'Receive request ping: {params}')
        await verbose_ping(display=self.send_msg, **params)

    async def imitate_telnet(self, dest_ip, dest_port=23, timeout=10):
        params = {
            'dest_ip': dest_ip, 'dest_port': dest_port, 'timeout': timeout,
        }
        logger.info(f'Receive request telnet: {params}')
        await verbose_telnet(display=self.send_msg, **params)

    async def imitate_nmap(self, dest_ips, dest_ports=None, timeout=None):
        params = {
            'dest_ips': dest_ips, 'dest_ports': dest_ports, 'timeout': timeout,
        }
        logger.info(f'Receive request nmap: {params}')
        await verbose_nmap(display=self.send_msg, **params)

    async def imitate_tcpdump(
            self, interfaces=None, src_ips='',
            src_ports='', dest_ips='', dest_ports=''
    ):
        params = {
            'interfaces': interfaces, 'src_ips': src_ips, 'src_ports': src_ports,
            'dest_ips': dest_ips, 'dest_ports': dest_ports
        }
        logger.info(f'Receive request tcpdump: {params}')
        await verbose_tcpdump(display=self.send_msg, **params)

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        data = json.loads(text_data)
        tool_type = data.pop('tool_type', 'Ping')
        try:
            tool_func = getattr(self, f'imitate_{tool_type.lower()}')
            await tool_func(**data)
        except Exception as error:
            await self.send_msg('Exception: %s' % error)
        await self.send_msg()
        await self.close()

    async def disconnect(self, code):
        await self.close()
        close_old_connections()
