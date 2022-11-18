# -*- coding: utf-8 -*-
#
from collections import defaultdict

from django.db.models import TextChoices
from django.utils.translation import ugettext_lazy as _

from assets.const import Protocol


# Replay & Command Storage Choices
# --------------------------------


class ReplayStorageType(TextChoices):
    null = 'null', 'Null',
    server = 'server', 'Server'
    s3 = 's3', 'S3'
    ceph = 'ceph', 'Ceph'
    swift = 'swift', 'Swift'
    oss = 'oss', 'OSS'
    azure = 'azure', 'Azure'
    obs = 'obs', 'OBS'
    cos = 'cos', 'COS'


class CommandStorageType(TextChoices):
    null = 'null', 'Null',
    server = 'server', 'Server'
    es = 'es', 'Elasticsearch'


# Component Status Choices
# ------------------------

class ComponentLoad(TextChoices):
    critical = 'critical', _('Critical')
    high = 'high', _('High')
    normal = 'normal', _('Normal')
    offline = 'offline', _('Offline')

    @classmethod
    def status(cls):
        return set(dict(cls.choices).keys())


class HttpMethod(TextChoices):
    web_gui = 'web_gui', 'Web GUI'
    web_cli = 'web_cli', 'Web CLI'


class NativeClient(TextChoices):
    # Koko
    ssh = 'ssh', 'SSH'
    putty = 'putty', 'PuTTY'
    xshell = 'xshell', 'Xshell'

    # Magnus
    mysql = 'mysql', 'mysql'
    psql = 'psql', 'psql'
    sqlplus = 'sqlplus', 'sqlplus'
    redis = 'redis-cli', 'redis-cli'
    mongodb = 'mongo', 'mongo'

    # Razor
    mstsc = 'mstsc', 'Remote Desktop'

    @classmethod
    def get_native_clients(cls):
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
    def get_methods(cls, os='windows'):
        clients_map = cls.get_native_clients()
        methods = defaultdict(list)

        for protocol, _clients in clients_map.items():
            if isinstance(_clients, dict):
                _clients = _clients.get(os, _clients['default'])
            for client in _clients:
                methods[protocol].append({
                    'value': client.value,
                    'label': client.label,
                    'type': 'native',
                })
        return methods

    @classmethod
    def get_launch_command(cls, name, os='windows'):
        commands = {
            'ssh': 'ssh {username}@{hostname} -p {port}',
            'putty': 'putty -ssh {username}@{hostname} -P {port}',
            'xshell': '-url ssh://root:passwd@192.168.10.100',
            'mysql': 'mysql -h {hostname} -P {port} -u {username} -p',
            'psql': {
                'default': 'psql -h {hostname} -p {port} -U {username} -W',
                'windows': 'psql /h {hostname} /p {port} /U {username} -W',
            },
            'sqlplus': 'sqlplus {username}/{password}@{hostname}:{port}',
            'redis': 'redis-cli -h {hostname} -p {port} -a {password}',
            'mstsc': 'mstsc /v:{hostname}:{port}',
        }
        command = commands.get(name)
        if isinstance(command, dict):
            command = command.get(os, command.get('default'))
        return command


class AppletMethod:
    @classmethod
    def get_methods(cls):
        from .models import Applet
        applets = Applet.objects.all()
        methods = defaultdict(list)
        for applet in applets:
            for protocol in applet.protocols:
                methods[protocol].append({
                    'value': applet.name,
                    'label': applet.display_name,
                    'icon': applet.icon,
                })
        return methods


class TerminalType(TextChoices):
    koko = 'koko', 'KoKo'
    guacamole = 'guacamole', 'Guacamole'
    omnidb = 'omnidb', 'OmniDB'
    xrdp = 'xrdp', 'Xrdp'
    lion = 'lion', 'Lion'
    core = 'core', 'Core'
    celery = 'celery', 'Celery'
    magnus = 'magnus', 'Magnus'
    razor = 'razor', 'Razor'
    tinker = 'tinker', 'Tinker'

    @classmethod
    def types(cls):
        return set(dict(cls.choices).keys())

    @classmethod
    def protocols(cls):
        protocols = {
            cls.koko: {
                'web_method': HttpMethod.web_cli,
                'listen': [Protocol.ssh, Protocol.http],
                'support': [
                    Protocol.ssh, Protocol.telnet,
                    Protocol.mysql, Protocol.postgresql,
                    Protocol.oracle, Protocol.sqlserver,
                    Protocol.mariadb, Protocol.redis,
                    Protocol.mongodb, Protocol.k8s,
                ],
                'match': 'm2m'
            },
            cls.omnidb: {
                'web_method': HttpMethod.web_gui,
                'listen': [Protocol.http],
                'support': [
                    Protocol.mysql, Protocol.postgresql, Protocol.oracle,
                    Protocol.sqlserver, Protocol.mariadb
                ],
                'match': 'm2m'
            },
            cls.lion: {
                'web_method': HttpMethod.web_gui,
                'listen': [Protocol.http],
                'support': [Protocol.rdp, Protocol.vnc],
                'match': 'm2m'
            },
            cls.magnus: {
                'listen': [],
                'support': [
                    Protocol.mysql, Protocol.postgresql, Protocol.oracle,
                    Protocol.mariadb
                ],
                'match': 'map'
            },
            cls.razor: {
                'listen': [Protocol.rdp],
                'support': [Protocol.rdp],
                'match': 'map'
            },
        }
        return protocols

    @classmethod
    def get_protocols_connect_methods(cls, os):
        methods = defaultdict(list)
        native_methods = NativeClient.get_methods(os)
        applet_methods = AppletMethod.get_methods()

        for component, component_protocol in cls.protocols().items():
            support = component_protocol['support']

            for protocol in support:
                if component_protocol['match'] == 'map':
                    listen = [protocol]
                else:
                    listen = component_protocol['listen']

                for listen_protocol in listen:
                    if listen_protocol == Protocol.http:
                        web_protocol = component_protocol['web_method']
                        methods[protocol.value].append({
                            'value': web_protocol.value,
                            'label': web_protocol.label,
                            'type': 'web',
                            'component': component.value,
                        })

                    # Native method
                    methods[protocol.value].extend([
                        {'component': component.value, 'type': 'native', **method}
                        for method in native_methods[listen_protocol]
                    ])

        for protocol, applet_methods in applet_methods.items():
            for method in applet_methods:
                method['type'] = 'applet'
                method['component'] = cls.tinker.value
            methods[protocol].extend(applet_methods)
        return methods
