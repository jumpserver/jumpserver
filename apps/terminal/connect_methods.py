# -*- coding: utf-8 -*-
#
import itertools
from collections import defaultdict

from django.conf import settings
from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _

from assets.const import Protocol
from .const import TerminalType


class WebMethod(TextChoices):
    web_gui = 'web_gui', 'Web GUI'
    web_cli = 'web_cli', 'Web CLI'
    web_sftp = 'web_sftp', 'Web SFTP'

    @classmethod
    def get_spec_methods(cls):
        methods = {
            Protocol.sftp: [cls.web_sftp]
        }
        return methods


class NativeClient(TextChoices):
    # Koko
    ssh_client = 'ssh_client', _('SSH Client')
    ssh_guide = 'ssh_guide', _('SSH Guide')
    sftp_client = 'sftp_client', _('SFTP Client')
    # Magnus
    db_guide = 'db_guide', _('DB Guide')
    db_client = 'db_client', _('DB Client')
    # Razor
    mstsc = 'mstsc', _('Remote Desktop')

    @classmethod
    def get_native_clients(cls):
        # native client 关注的是 endpoint 的 protocol,
        # 比如 telnet mysql, koko 都支持，到那时暴露的是 ssh 协议
        clients = {
            Protocol.ssh: [cls.ssh_client, cls.ssh_guide],
            Protocol.sftp: [cls.sftp_client],
            Protocol.rdp: [cls.mstsc],
            Protocol.mysql: [cls.db_client, cls.db_guide],
            Protocol.mariadb: [cls.db_client, cls.db_guide],
            Protocol.redis: [cls.db_client, cls.db_guide],
            Protocol.mongodb: [cls.db_client, cls.db_guide],
            Protocol.oracle: [cls.db_client, cls.db_guide],
            Protocol.postgresql: [cls.db_client, cls.db_guide],
            Protocol.sqlserver: [cls.db_client, cls.db_guide],
        }
        return clients

    @classmethod
    def get_target_protocol(cls, name, os):
        for protocol, clients in cls.get_native_clients().items():
            if isinstance(clients, dict):
                if os == 'all':
                    clients = list(itertools.chain(*clients.values()))
                else:
                    clients = clients.get(os) or clients.get('default')
            if name in clients:
                return protocol
        return None

    @classmethod
    def xpack_methods(cls):
        return [cls.mstsc]

    @classmethod
    def get_methods(cls, os='windows'):
        clients_map = cls.get_native_clients()
        methods = defaultdict(list)
        xpack_protocols = Protocol.xpack_protocols()

        for protocol, _clients in clients_map.items():
            if not settings.XPACK_LICENSE_IS_VALID and protocol in xpack_protocols:
                continue
            if isinstance(_clients, dict):
                if os == 'all':
                    _clients = list(itertools.chain(*_clients.values()))
                else:
                    _clients = _clients.get(os, _clients['default'])
            for client in _clients:
                if not settings.XPACK_LICENSE_IS_VALID and client in cls.xpack_methods():
                    continue
                methods[protocol].append({
                    'value': client.value,
                    'label': client.label,
                    'type': 'native',
                })
        return methods


class AppletMethod:
    @classmethod
    def get_methods(cls):
        from .models import Applet, AppletHost

        methods = defaultdict(list)
        has_applet_hosts = AppletHost.objects.all().exists()
        applets = Applet.objects.filter(is_active=True)
        for applet in applets:
            for protocol in applet.protocols:
                methods[protocol].append({
                    'value': applet.name,
                    'label': applet.display_name,
                    'type': 'applet',
                    'icon': applet.icon,
                    'disabled': not applet.is_active or not has_applet_hosts,
                })
        return methods


class VirtualAppMethod:

    @classmethod
    def get_methods(cls):
        from .models import VirtualApp
        methods = defaultdict(list)
        if not getattr(settings, 'VIRTUAL_APP_ENABLED'):
            return methods
        virtual_apps = VirtualApp.objects.filter(is_active=True)
        for virtual_app in virtual_apps:
            for protocol in virtual_app.protocols:
                methods[protocol].append({
                    'value': virtual_app.name,
                    'label': virtual_app.name,
                    'type': 'virtual_app',
                    'disabled': not virtual_app.is_active,
                })
        return methods


class ConnectMethodUtil:
    _all_methods = {}

    @classmethod
    def components(cls):
        protocols = {
            TerminalType.koko: {
                'web_methods': [WebMethod.web_cli],
                'listen': [Protocol.http, Protocol.ssh, Protocol.sftp],
                'support': [
                    Protocol.ssh, Protocol.telnet, Protocol.sftp,
                    Protocol.redis, Protocol.mongodb,
                    Protocol.k8s, Protocol.clickhouse,

                    Protocol.mysql, Protocol.mariadb,
                    Protocol.sqlserver, Protocol.postgresql,
                ],
                # 限制客户端的协议，比如 koko 虽然也支持 数据库的 ssh 连接，但是不再这里拉起
                # Listen协议: [Asset协议]
                'client_limits': {
                    Protocol.sftp: [Protocol.sftp],
                    Protocol.ssh: [Protocol.ssh, Protocol.telnet],
                },
                'match': 'm2m'
            },
            TerminalType.chen: {
                'web_methods': [WebMethod.web_gui],
                'listen': [Protocol.http],
                'support': [
                    Protocol.mysql, Protocol.postgresql,
                    Protocol.oracle, Protocol.sqlserver,
                    Protocol.mariadb, Protocol.db2
                ],
                'match': 'm2m'
            },
            TerminalType.lion: {
                'web_methods': [WebMethod.web_gui],
                'listen': [Protocol.http],
                'support': [Protocol.rdp, Protocol.vnc],
                'match': 'm2m'
            },
            TerminalType.magnus: {
                'web_methods': [],
                'listen': [],
                'support': [
                    Protocol.mysql, Protocol.postgresql,
                    Protocol.oracle, Protocol.mariadb,
                    Protocol.redis, Protocol.sqlserver
                ],
                'match': 'map'
            },
            TerminalType.razor: {
                'web_methods': [],
                'listen': [Protocol.rdp],
                'support': [Protocol.rdp],
                'match': 'map'
            },
            TerminalType.kael: {
                'web_methods': [WebMethod.web_gui],
                'listen': [Protocol.http],
                'support': [Protocol.chatgpt],
                'match': 'm2m'
            }
        }
        return protocols

    @classmethod
    def get_connect_method(cls, name, protocol, os='linux'):
        methods = cls.get_protocols_connect_methods(os)
        protocol_methods = methods.get(protocol, [])
        for method in protocol_methods:
            if method['value'] == name:
                return method
        return None

    @classmethod
    def refresh_methods(cls):
        cls._all_methods = {}

    @classmethod
    def get_filtered_protocols_connect_methods(cls, os):
        methods = dict(cls.get_protocols_connect_methods(os))
        methods = cls._filter_disable_components_connect_methods(methods)
        methods = cls._filter_disable_protocols_connect_methods(methods)
        return methods

    @classmethod
    def get_user_allowed_connect_methods(cls, os, user):
        from acls.models import ConnectMethodACL
        methods = cls.get_filtered_protocols_connect_methods(os)
        acls = ConnectMethodACL.get_user_acls(user)
        disabled_connect_methods = acls.values_list('connect_methods', flat=True)
        disabled_connect_methods = set(itertools.chain.from_iterable(disabled_connect_methods))

        new_queryset = {}
        for protocol, methods in methods.items():
            new_queryset[protocol] = [x for x in methods if x['value'] not in disabled_connect_methods]
        return new_queryset

    @classmethod
    def _filter_disable_components_connect_methods(cls, methods):
        component_setting = {
            'razor': 'TERMINAL_RAZOR_ENABLED',
            'magnus': 'TERMINAL_MAGNUS_ENABLED',
        }
        disabled_component = [comp for comp, attr in component_setting.items() if not getattr(settings, attr)]
        if not disabled_component:
            return methods

        for protocol, ms in methods.items():
            filtered_methods = [m for m in ms if m['component'] not in disabled_component]
            methods[protocol] = filtered_methods
        return methods

    @classmethod
    def _filter_disable_protocols_connect_methods(cls, methods):
        # 过滤一些特殊的协议方式
        if not getattr(settings, 'TERMINAL_KOKO_SSH_ENABLED'):
            protocol = Protocol.ssh
            methods[protocol] = [m for m in methods[protocol] if m['type'] != 'native']
        return methods

    @classmethod
    def get_protocols_connect_methods(cls, os='windows'):
        if cls._all_methods.get('os'):
            return cls._all_methods['os']

        methods = defaultdict(list)
        spec_web_methods = WebMethod.get_spec_methods()
        applet_methods = AppletMethod.get_methods()
        virtual_app_methods = VirtualAppMethod.get_methods()
        native_methods = NativeClient.get_methods(os=os)

        for component, component_protocol in cls.components().items():
            support = component_protocol['support']
            default_web_methods = component_protocol.get('web_methods', [])
            client_limits = component_protocol.get('client_limits', {})

            for asset_protocol in support:
                # Web 方式
                web_methods = spec_web_methods.get(asset_protocol, [])
                if not web_methods:
                    web_methods = default_web_methods
                methods[str(asset_protocol)].extend([
                    {
                        'component': component.value,
                        'type': 'web',
                        'endpoint_protocol': 'http',
                        'value': method.value,
                        'label': method.label,
                    }
                    for method in web_methods
                ])

                # 客户端方式
                if component_protocol['match'] == 'map':
                    listen = [asset_protocol]
                else:
                    listen = component_protocol['listen']

                for listen_protocol in listen:
                    limits = client_limits.get(listen_protocol, [])
                    if limits and asset_protocol not in limits:
                        continue
                    # Native method
                    client_methods = native_methods.get(listen_protocol, [])
                    methods[str(asset_protocol)].extend([
                        {
                            'component': component.value,
                            'type': 'native',
                            'endpoint_protocol': listen_protocol,
                            **method
                        }
                        for method in client_methods
                    ])

        # 远程应用方式，这个只有 tinker 提供，并且协议可能是自定义的
        for asset_protocol, applet_methods in applet_methods.items():
            for method in applet_methods:
                method['listen'] = 'rdp'
                method['component'] = TerminalType.tinker.value
            methods[asset_protocol].extend(applet_methods)

        # 虚拟应用方式，这个只有 panda 提供，并且协议可能是自定义的
        for protocol, virtual_app_methods in virtual_app_methods.items():
            for method in virtual_app_methods:
                method['listen'] = Protocol.http
                method['component'] = TerminalType.panda.value
            methods[protocol].extend(virtual_app_methods)

        cls._all_methods[os] = methods
        return methods
