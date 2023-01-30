# -*- coding: utf-8 -*-
#
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
        return {
            Protocol.ssh: [cls.web_cli, cls.web_sftp],
            Protocol.telnet: [cls.web_cli],
            Protocol.rdp: [cls.web_gui],
            Protocol.vnc: [cls.web_gui],

            Protocol.mysql: [cls.web_cli, cls.web_gui],
            Protocol.mariadb: [cls.web_cli, cls.web_gui],
            Protocol.oracle: [cls.web_cli, cls.web_gui],
            Protocol.postgresql: [cls.web_cli, cls.web_gui],
            Protocol.sqlserver: [cls.web_cli, cls.web_gui],
            Protocol.redis: [cls.web_cli],
            Protocol.mongodb: [cls.web_cli],
            Protocol.clickhouse: [cls.web_cli],

            Protocol.k8s: [cls.web_cli],
            Protocol.http: []
        }


class NativeClient(TextChoices):
    # Koko
    ssh = 'ssh', 'SSH'
    putty = 'putty', 'PuTTY'
    xshell = 'xshell', 'Xshell'

    # Magnus
    mysql = 'db_client_mysql', _('DB Client')
    psql = 'db_client_psql', _('DB Client')
    sqlplus = 'db_client_sqlplus', _('DB Client')
    redis = 'db_client_redis', _('DB Client')
    mongodb = 'db_client_mongodb', _('DB Client')

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
            Protocol.mysql: [cls.mysql],
            Protocol.oracle: [cls.sqlplus],
            Protocol.postgresql: [cls.psql],
            Protocol.redis: [cls.redis],
            Protocol.mongodb: [cls.mongodb],
        }
        return clients

    @classmethod
    def get_target_protocol(cls, name, os):
        for protocol, clients in cls.get_native_clients().items():
            if isinstance(clients, dict):
                clients = clients.get(os) or clients.get('default')
            if name in clients:
                return protocol
        return None

    @classmethod
    def xpack_methods(cls):
        return [cls.sqlplus, cls.mstsc]

    @classmethod
    def get_methods(cls, os='windows'):
        clients_map = cls.get_native_clients()
        methods = defaultdict(list)

        for protocol, _clients in clients_map.items():
            if isinstance(_clients, dict):
                _clients = _clients.get(os, _clients['default'])
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
        if not settings.XPACK_ENABLED:
            return methods

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
    _all_methods = None

    @classmethod
    def protocols(cls):
        protocols = {
            TerminalType.koko: {
                'web_methods': [WebMethod.web_cli, WebMethod.web_sftp],
                'listen': [Protocol.http],
                'support': [
                    Protocol.ssh, Protocol.telnet,
                    Protocol.mysql, Protocol.postgresql,
                    Protocol.oracle, Protocol.sqlserver,
                    Protocol.mariadb, Protocol.redis,
                    Protocol.mongodb, Protocol.k8s,
                    Protocol.clickhouse,
                ],
                'match': 'm2m'
            },
            TerminalType.omnidb: {
                'web_methods': [WebMethod.web_gui],
                'listen': [Protocol.http],
                'support': [
                    Protocol.mysql, Protocol.postgresql, Protocol.oracle,
                    Protocol.sqlserver, Protocol.mariadb
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
                'listen': [],
                'support': [
                    Protocol.mysql, Protocol.postgresql,
                    Protocol.oracle, Protocol.mariadb,
                    Protocol.redis
                ],
                'match': 'map'
            },
            TerminalType.razor: {
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
        cls._all_methods = None

    @classmethod
    def get_protocols_connect_methods(cls, os):
        if cls._all_methods is not None:
            return cls._all_methods

        methods = defaultdict(list)
        web_methods = WebMethod.get_methods()
        native_methods = NativeClient.get_methods(os)
        applet_methods = AppletMethod.get_methods()

        for component, component_protocol in cls.protocols().items():
            support = component_protocol['support']
            component_web_methods = component_protocol.get('web_methods', [])

            for protocol in support:
                # Web 方式
                methods[protocol.value].extend([
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
                    methods[protocol.value].extend([
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

        cls._all_methods = methods
        return methods
