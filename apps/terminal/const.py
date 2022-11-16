# -*- coding: utf-8 -*-
#

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


class NativeClient:
    # Koko
    ssh = 'ssh', 'ssh'
    putty = 'putty', 'PuTTY'
    xshell = 'xshell', 'Xshell'

    # Magnus
    mysql = 'mysql', 'MySQL Client'
    psql = 'psql', 'psql'
    sqlplus = 'sqlplus', 'sqlplus'
    redis = 'redis-cli', 'redis-cli'

    # Razor
    mstsc = 'mstsc', 'Remote Desktop'

    @classmethod
    def commands(cls, name, os):
        return {
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


class ConnectMethod(TextChoices):
    web_cli = 'web_cli', _('Web CLI')
    web_gui = 'web_gui', _('Web GUI')
    native_client = 'native_client', _('Native Client')

    @classmethod
    def methods(cls):
        return {
            Protocol.ssh: [cls.web_cli, cls.native_client],
            Protocol.rdp: ([cls.web_gui], [cls.native_client]),
            Protocol.vnc: [cls.web_gui],
            Protocol.telnet: [cls.web_cli, cls.native_client],
            Protocol.mysql: [cls.web_cli, cls.web_gui, cls.native_client],
            Protocol.sqlserver: [cls.web_cli, cls.web_gui],
        }
