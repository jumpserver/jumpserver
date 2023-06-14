# -*- coding: utf-8 -*-
#
import itertools
from collections import defaultdict

from django.conf import settings
from django.db.models import TextChoices
from django.utils.translation import ugettext_lazy as _

from assets.const import Protocol
from .const import TerminalType


class WebMethod(TextChoices):
    web_gui = 'web_gui', 'Web GUI'
    web_cli = 'web_cli', 'Web CLI'
    web_sftp = 'web_sftp', 'Web SFTP'

    @classmethod
    def get_methods(cls):
        methods = {
            Protocol.ssh: [cls.web_cli, cls.web_sftp],
            Protocol.telnet: [cls.web_cli],
            Protocol.rdp: [cls.web_gui],
            Protocol.vnc: [cls.web_gui],

            Protocol.mysql: [cls.web_cli],
            Protocol.mariadb: [cls.web_cli],
            Protocol.oracle: [cls.web_cli],
            Protocol.postgresql: [cls.web_cli],
            Protocol.sqlserver: [cls.web_cli],
            Protocol.redis: [cls.web_cli],
            Protocol.mongodb: [cls.web_cli],
            Protocol.clickhouse: [cls.web_cli],

            Protocol.k8s: [cls.web_cli],
            Protocol.http: []
        }
        if not settings.XPACK_ENABLED:
            return methods

        web_gui_dbs = [Protocol.mysql, Protocol.mariadb, Protocol.oracle, Protocol.postgresql]
        for db in web_gui_dbs:
            methods[db].append(cls.web_gui)
        return methods


class NativeClient(TextChoices):
    # Koko
    ssh = 'ssh', 'SSH'
    putty = 'putty', 'PuTTY'
    xshell = 'xshell', 'Xshell'

    # Magnus
    db_client = 'db_client', _('DB Client')

    # Razor
    mstsc = 'mstsc', 'Remote Desktop'

    @classmethod
    def get_native_clients(cls):
        # native client 关注的是 endpoint 的 protocol,
        # 比如 telnet mysql, koko 都支持，到那时暴露的是 ssh 协议
        clients = {
            Protocol.ssh: {
                'default': [cls.ssh],
                'windows': [cls.putty],
            },
            Protocol.rdp: [cls.mstsc],
            Protocol.mysql: [cls.db_client],
            Protocol.mariadb: [cls.db_client],
            Protocol.redis: [cls.db_client],
            Protocol.mongodb: [cls.db_client],

            Protocol.oracle: [cls.db_client],
            Protocol.postgresql: [cls.db_client],
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
    def xpack_protocols(cls):
        return [Protocol.rdp, Protocol.oracle, Protocol.clickhouse, Protocol.sqlserver]

    @classmethod
    def get_methods(cls, os='windows'):
        clients_map = cls.get_native_clients()
        methods = defaultdict(list)
        xpack_protocols = cls.xpack_protocols()

        for protocol, _clients in clients_map.items():
            if isinstance(_clients, dict):
                if os == 'all':
                    _clients = list(itertools.chain(*_clients.values()))
                else:
                    _clients = _clients.get(os, _clients['default'])
            if protocol in xpack_protocols:
                continue
            for client in _clients:
                if not settings.XPACK_ENABLED and client in cls.xpack_methods():
                    continue
                methods[protocol].append({
                    'value': client.value,
                    'label': client.label,
                    'type': 'native',
                })
        return methods

    @classmethod
    def get_launch_command(cls, name, token, endpoint, os='windows'):
        username = f'JMS-{token.id}'
        commands = {
            cls.ssh: f'ssh {username}@{endpoint.host} -p {endpoint.ssh_port}',
            cls.putty: f'putty.exe -ssh {username}@{endpoint.host} -P {endpoint.ssh_port}',
            cls.xshell: f'xshell.exe -url ssh://{username}:{token.value}@{endpoint.host}:{endpoint.ssh_port}',
            # cls.mysql: 'mysql -h {hostname} -P {port} -u {username} -p',
            # cls.psql: {
            #     'default': 'psql -h {hostname} -p {port} -U {username} -W',
            #     'windows': 'psql /h {hostname} /p {port} /U {username} -W',
            # },
            # cls.sqlplus: 'sqlplus {username}/{password}@{hostname}:{port}',
            # cls.redis: 'redis-cli -h {hostname} -p {port} -a {password}',
        }
        command = commands.get(name)
        if isinstance(command, dict):
            command = command.get(os, command.get('default'))
        return command


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


class ConnectMethodUtil:
    _all_methods = {}

    @classmethod
    def protocols(cls):
        protocols = {
            TerminalType.koko: {
                'web_methods': [WebMethod.web_cli, WebMethod.web_sftp],
                'listen': [Protocol.http, Protocol.ssh],
                'support': [
                    Protocol.ssh, Protocol.telnet,
                    Protocol.mysql, Protocol.postgresql,
                    Protocol.sqlserver, Protocol.mariadb,
                    Protocol.redis, Protocol.mongodb,
                    Protocol.k8s, Protocol.clickhouse,
                ],
                'match': 'm2m'
            },
            TerminalType.omnidb: {
                'web_methods': [WebMethod.web_gui],
                'listen': [Protocol.http],
                'support': [
                    Protocol.mysql, Protocol.postgresql,
                    Protocol.oracle, Protocol.mariadb
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
                    Protocol.redis
                ],
                'match': 'map'
            },
            TerminalType.razor: {
                'web_methods': [],
                'listen': [Protocol.rdp],
                'support': [Protocol.rdp],
                'match': 'map'
            },
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
        web_methods = WebMethod.get_methods()
        native_methods = NativeClient.get_methods(os)
        applet_methods = AppletMethod.get_methods()

        for component, component_protocol in cls.protocols().items():
            support = component_protocol['support']
            component_web_methods = component_protocol.get('web_methods', [])

            for protocol in support:
                # Web 方式
                methods[str(protocol)].extend([
                    {
                        'component': component.value,
                        'type': 'web',
                        'endpoint_protocol': 'http',
                        'value': method.value,
                        'label': method.label,
                    }
                    for method in web_methods.get(protocol, [])
                    if method in component_web_methods
                ])

                # 客户端方式
                if component_protocol['match'] == 'map':
                    listen = [protocol]
                else:
                    listen = component_protocol['listen']
                for listen_protocol in listen:
                    # Native method
                    if component == TerminalType.koko and protocol.value != Protocol.ssh:
                        # koko 仅支持 ssh 的 native 方式，其他数据库的 native 方式不提供
                        continue
                    methods[str(protocol)].extend([
                        {
                            'component': component.value,
                            'type': 'native',
                            'endpoint_protocol': listen_protocol,
                            **method
                        }
                        for method in native_methods[listen_protocol]
                    ])

        # 远程应用方式，这个只有 tinker 提供
        for protocol, applet_methods in applet_methods.items():
            for method in applet_methods:
                method['listen'] = 'rdp'
                method['component'] = TerminalType.tinker.value
            methods[protocol].extend(applet_methods)

        cls._all_methods[os] = methods
        return methods
