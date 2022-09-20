from django.db import models
from common.db.models import ChoicesMixin

__all__ = ['Protocol']


class Protocol(ChoicesMixin, models.TextChoices):
    ssh = 'ssh', 'SSH'
    rdp = 'rdp', 'RDP'
    telnet = 'telnet', 'Telnet'
    vnc = 'vnc', 'VNC'

    mysql = 'mysql', 'MySQL'
    mariadb = 'mariadb', 'MariaDB'
    oracle = 'oracle', 'Oracle'
    postgresql = 'postgresql', 'PostgreSQL'
    sqlserver = 'sqlserver', 'SQLServer'
    redis = 'redis', 'Redis'
    mongodb = 'mongodb', 'MongoDB'

    k8s = 'k8s', 'K8S'
    http = 'http', 'HTTP'
    https = 'https', 'HTTPS'

    @classmethod
    def device_settings(cls):
        return {
            cls.ssh: {
                'port': 22,
                'secret_type': ['password', 'ssh_key'],
                'setting': {
                    'sftp_enabled': True,
                    'sftp_home': '/tmp',
                }
            },
            cls.rdp: {
                'port': 3389,
                'secret_type': ['password'],
                'setting': {
                    'console': True,
                    'security': 'any',
                }
            },
            cls.vnc: {
                'port': 5900,
                'secret_type': ['password'],
            },
            cls.telnet: {
                'port': 23,
                'secret_type': ['password'],
            },
        }

    @classmethod
    def db_settings(cls):
        return {
            cls.mysql: {
                'port': 3306,
                'secret_type': ['password'],
                'setting': {
                }
            },
            cls.mariadb: {
                'port': 3306,
                'secret_type': ['password'],
            },
            cls.postgresql: {
                'port': 5432,
                'secret_type': ['password'],
            },
            cls.oracle: {
                'port': 1521,
                'secret_type': ['password'],
            },
            cls.sqlserver: {
                'port': 1433,
                'secret_type': ['password'],
            },
            cls.mongodb: {
                'port': 27017,
                'secret_type': ['password'],
            },
            cls.redis: {
                'port': 6379,
                'secret_type': ['password'],
            },
        }

    @classmethod
    def cloud_settings(cls):
        return {
            cls.k8s: {
                'port': 443,
                'secret_type': ['token'],
                'setting': {
                    'via_http': True
                }
            },
            cls.http: {
                'port': 80,
                'secret_type': ['password'],
                'setting': {
                    'ssl': True
                }
            },
        }

    @classmethod
    def settings(cls):
        return {
            **cls.device_settings(),
            **cls.db_settings(),
            **cls.cloud_settings()
        }

    @classmethod
    def default_ports(cls):
        return {
            cls.ssh: 22,
            cls.sftp: 22,
            cls.rdp: 3389,
            cls.vnc: 5900,
            cls.telnet: 21,

            cls.mysql: 3306,
            cls.mariadb: 3306,
            cls.postgresql: 5432,
            cls.oracle: 1521,
            cls.sqlserver: 1433,
            cls.mongodb: 27017,
            cls.redis: 6379,

            cls.k8s: 0,

            cls.http: 80,
        }

