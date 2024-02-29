# -*- coding: utf-8 -*-
#
import json
import asyncio

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.core.cache import cache
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from common.db.utils import close_old_connections
from common.utils import get_logger
from settings.serializers import (
    LDAPTestConfigSerializer,
    LDAPTestLoginSerializer
)
from orgs.models import Organization
from orgs.utils import current_org
from settings.tasks import sync_ldap_user
from settings.utils import (
    LDAPServerUtil, LDAPCacheUtil, LDAPImportUtil, LDAPSyncUtil,
    LDAP_USE_CACHE_FLAGS, LDAPTestUtil
)
from .tools import (
    verbose_ping, verbose_telnet, verbose_nmap,
    verbose_tcpdump, verbose_traceroute
)

logger = get_logger(__name__)

CACHE_KEY_LDAP_TEST_CONFIG_MSG = 'CACHE_KEY_LDAP_TEST_CONFIG_MSG'
CACHE_KEY_LDAP_TEST_LOGIN_MSG = 'CACHE_KEY_LDAP_TEST_LOGIN_MSG'
CACHE_KEY_LDAP_SYNC_USER_MSG = 'CACHE_KEY_LDAP_SYNC_USER_MSG'
CACHE_KEY_LDAP_IMPORT_USER_MSG = 'CACHE_KEY_LDAP_IMPORT_USER_MSG'
CACHE_KEY_LDAP_TEST_CONFIG_TASK_STATUS = 'CACHE_KEY_LDAP_TEST_CONFIG_TASK_STATUS'
CACHE_KEY_LDAP_TEST_LOGIN_TASK_STATUS = 'CACHE_KEY_LDAP_TEST_LOGIN_TASK_STATUS'
CACHE_KEY_LDAP_SYNC_USER_TASK_STATUS = 'CACHE_KEY_LDAP_SYNC_USER_TASK_STATUS'
CACHE_KEY_LDAP_IMPORT_USER_TASK_STATUS = 'CACHE_KEY_LDAP_IMPORT_USER_TASK_STATUS'
TASK_STATUS_IS_RUNNING = 'RUNNING'
TASK_STATUS_IS_OVER = 'OVER'


class ToolsWebsocket(AsyncJsonWebsocketConsumer):

    async def connect(self):
        user = self.scope["user"]
        if user.is_authenticated:
            await self.accept()
        else:
            await self.close()

    async def send_msg(self, msg=''):
        await self.send_json({'msg': f'{msg}\r\n'})

    async def imitate_ping(self, dest_ips, timeout=3, count=5, psize=64):
        params = {
            'dest_ips': dest_ips, 'timeout': timeout,
            'count': count, 'psize': psize
        }
        logger.info(f'Receive request ping: {params}')
        await verbose_ping(display=self.send_msg, **params)

    async def imitate_telnet(self, dest_ips, dest_port=23, timeout=10):
        params = {
            'dest_ips': dest_ips, 'dest_port': dest_port, 'timeout': timeout,
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

    async def imitate_traceroute(self, dest_ips):
        params = {'dest_ips': dest_ips}
        await verbose_traceroute(display=self.send_msg, **params)

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


class LdapWebsocket(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if user.is_authenticated:
            await self.accept()
        else:
            await self.close()

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        data = json.loads(text_data)
        msg_type = data.pop('msg_type', 'testing_config')
        try:
            tool_func = getattr(self, f'run_{msg_type.lower()}')
            await asyncio.to_thread(tool_func, data)
            if msg_type == 'testing_config':
                ok, msg = cache.get(CACHE_KEY_LDAP_TEST_CONFIG_MSG)
            elif msg_type == 'sync_user':
                ok, msg = cache.get(CACHE_KEY_LDAP_SYNC_USER_MSG)
            elif msg_type == 'import_user':
                ok, msg = cache.get(CACHE_KEY_LDAP_IMPORT_USER_MSG)
            else:
                ok, msg = cache.get(CACHE_KEY_LDAP_TEST_LOGIN_MSG)
            await self.send_msg(ok, msg)
        except Exception as error:
            await self.send_msg(msg='Exception: %s' % error)

    async def send_msg(self, ok=True, msg=''):
        await self.send_json({'ok': ok, 'msg': f'{msg}'})

    async def disconnect(self, code):
        await self.close()
        close_old_connections()

    @staticmethod
    def get_ldap_config(serializer):
        server_uri = serializer.validated_data["AUTH_LDAP_SERVER_URI"]
        bind_dn = serializer.validated_data["AUTH_LDAP_BIND_DN"]
        password = serializer.validated_data["AUTH_LDAP_BIND_PASSWORD"]
        use_ssl = serializer.validated_data.get("AUTH_LDAP_START_TLS", False)
        search_ou = serializer.validated_data["AUTH_LDAP_SEARCH_OU"]
        search_filter = serializer.validated_data["AUTH_LDAP_SEARCH_FILTER"]
        attr_map = serializer.validated_data["AUTH_LDAP_USER_ATTR_MAP"]
        auth_ldap = serializer.validated_data.get('AUTH_LDAP', False)

        if not password:
            password = settings.AUTH_LDAP_BIND_PASSWORD

        config = {
            'server_uri': server_uri,
            'bind_dn': bind_dn,
            'password': password,
            'use_ssl': use_ssl,
            'search_ou': search_ou,
            'search_filter': search_filter,
            'attr_map': attr_map,
            'auth_ldap': auth_ldap
        }
        return config

    @staticmethod
    def task_is_over(task_key):
        return cache.get(task_key) == TASK_STATUS_IS_OVER

    @staticmethod
    def set_task_status_over(task_key, ttl=120):
        cache.set(task_key, TASK_STATUS_IS_OVER, ttl)

    @staticmethod
    def set_task_msg(task_key, ok, msg, ttl=120):
        cache.set(task_key, (ok, msg), ttl)

    def run_testing_config(self, data):
        while True:
            if self.task_is_over(CACHE_KEY_LDAP_TEST_CONFIG_TASK_STATUS):
                break
            else:
                serializer = LDAPTestConfigSerializer(data=data)
                if not serializer.is_valid():
                    self.send_msg(msg=f'error: {str(serializer.errors)}')
                config = self.get_ldap_config(serializer)
                ok, msg = LDAPTestUtil(config).test_config()
                self.set_task_status_over(CACHE_KEY_LDAP_TEST_CONFIG_TASK_STATUS)
            self.set_task_msg(CACHE_KEY_LDAP_TEST_CONFIG_MSG, ok, msg)

    def run_testing_login(self, data):
        while True:
            if self.task_is_over(CACHE_KEY_LDAP_TEST_LOGIN_TASK_STATUS):
                break
            else:
                serializer = LDAPTestLoginSerializer(data=data)
                if not serializer.is_valid():
                    self.send_msg(msg=f'error: {str(serializer.errors)}')
                username = serializer.validated_data['username']
                password = serializer.validated_data['password']
                ok, msg = LDAPTestUtil().test_login(username, password)
                self.set_task_status_over(CACHE_KEY_LDAP_TEST_LOGIN_TASK_STATUS, 3)
            self.set_task_msg(CACHE_KEY_LDAP_TEST_LOGIN_MSG, ok, msg)

    def run_sync_user(self, data):
        while True:
            if self.task_is_over(CACHE_KEY_LDAP_SYNC_USER_TASK_STATUS):
                break
            else:
                sync_util = LDAPSyncUtil()
                sync_util.clear_cache()
                sync_ldap_user()
                msg = sync_util.get_task_error_msg()
                ok = False if msg else True
                self.set_task_status_over(CACHE_KEY_LDAP_SYNC_USER_TASK_STATUS)
            self.set_task_msg(CACHE_KEY_LDAP_SYNC_USER_MSG, ok, msg)

    def run_import_user(self, data):
        while True:
            if self.task_is_over(CACHE_KEY_LDAP_IMPORT_USER_TASK_STATUS):
                break
            else:
                ok, msg = self.import_user(data)
                self.set_task_status_over(CACHE_KEY_LDAP_IMPORT_USER_TASK_STATUS, 3)
            self.set_task_msg(CACHE_KEY_LDAP_IMPORT_USER_MSG, ok, msg, 3)

    def import_user(self, data):
        ok = False
        org_ids = data.get('org_ids')
        username_list = data.get('username_list', [])
        cache_police = data.get('cache_police', True)
        try:
            users = self.get_ldap_users(username_list, cache_police)
            if users is None:
                msg = _('Get ldap users is None')

            orgs = self.get_orgs(org_ids)
            new_users, error_msg = LDAPImportUtil().perform_import(users, orgs)
            if error_msg:
                msg = error_msg

            count = users if users is None else len(users)
            orgs_name = ', '.join([str(org) for org in orgs])
            ok = True
            msg = _('Imported {} users successfully (Organization: {})').format(count, orgs_name)
        except Exception as e:
            msg = str(e)
        return ok, msg

    @staticmethod
    def get_orgs(org_ids):
        if org_ids:
            orgs = list(Organization.objects.filter(id__in=org_ids))
        else:
            orgs = [current_org]
        return orgs

    @staticmethod
    def get_ldap_users(username_list, cache_police):
        if '*' in username_list:
            users = LDAPServerUtil().search()
        elif cache_police in LDAP_USE_CACHE_FLAGS:
            users = LDAPCacheUtil().search(search_users=username_list)
        else:
            users = LDAPServerUtil().search(search_users=username_list)
        return users
