from django.db import models

from common.db.models import ChoicesMixin

__all__ = ['Protocol']


class Protocol(ChoicesMixin, models.TextChoices):
    ssh = 'ssh', 'SSH'
    rdp = 'rdp', 'RDP'
    telnet = 'telnet', 'Telnet'
    vnc = 'vnc', 'VNC'
    winrm = 'winrm', 'WinRM'

    mysql = 'mysql', 'MySQL'
    mariadb = 'mariadb', 'MariaDB'
    oracle = 'oracle', 'Oracle'
    postgresql = 'postgresql', 'PostgreSQL'
    sqlserver = 'sqlserver', 'SQLServer'
    clickhouse = 'clickhouse', 'ClickHouse'
    redis = 'redis', 'Redis'
    mongodb = 'mongodb', 'MongoDB'

    k8s = 'k8s', 'K8S'
    http = 'http', 'HTTP'
    _settings = None

    @classmethod
    def device_protocols(cls):
        return {
            cls.ssh: {
                'port': 22,
                'secret_types': ['password', 'ssh_key'],
                'setting': {
                    'sftp_enabled': True,
                    'sftp_home': '/tmp',
                }
            },
            cls.rdp: {
                'port': 3389,
                'secret_types': ['password'],
                'setting': {
                    'console': False,
                    'security': 'any',
                }
            },
            cls.vnc: {
                'port': 5900,
                'secret_types': ['password'],
            },
            cls.telnet: {
                'port': 23,
                'secret_types': ['password'],
            },
            cls.winrm: {
                'port': 5985,
                'secret_types': ['password'],
                'setting': {
                    'use_ssl': False,
                }
            },
        }

    @classmethod
    def database_protocols(cls):
        return {
            cls.mysql: {
                'port': 3306,
                'setting': {},
                'required': True,
                'secret_types': ['password'],
            },
            cls.mariadb: {
                'port': 3306,
                'required': True,
                'secret_types': ['password'],
            },
            cls.postgresql: {
                'port': 5432,
                'required': True,
                'secret_types': ['password'],
            },
            cls.oracle: {
                'port': 1521,
                'required': True,
                'secret_types': ['password'],
            },
            cls.sqlserver: {
                'port': 1433,
                'required': True,
                'secret_types': ['password'],
            },
            cls.clickhouse: {
                'port': 9000,
                'required': True,
                'secret_types': ['password'],
            },
            cls.mongodb: {
                'port': 27017,
                'required': True,
                'secret_types': ['password'],
            },
            cls.redis: {
                'port': 6379,
                'required': True,
                'secret_types': ['password'],
                'setting': {
                    'auth_username': True,
                }
            },
        }

    @classmethod
    def cloud_protocols(cls):
        return {
            cls.k8s: {
                'port': 443,
                'required': True,
                'secret_types': ['token'],
            },
            cls.http: {
                'port': 80,
                'secret_types': ['password'],
                'setting': {
                    'username_selector': 'name=username',
                    'password_selector': 'name=password',
                    'submit_selector': 'id=login_button',
                }
            },
        }

    @classmethod
    def settings(cls):
        return {
            **cls.device_protocols(),
            **cls.database_protocols(),
            **cls.cloud_protocols()
        }

    @classmethod
    def protocol_secret_types(cls):
        settings = cls.settings()
        return {
            protocol: settings[protocol]['secret_types'] or ['password']
            for protocol in cls.settings()
        }
