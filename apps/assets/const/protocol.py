from django.db import models
from common.db.models import ChoicesMixin

__all__ = ['Protocol']


class Protocol(ChoicesMixin, models.TextChoices):
    ssh = 'ssh', 'SSH'
    sftp = 'sftp', 'SFTP'
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
    def host_protocols(cls):
        return [cls.ssh, cls.rdp, cls.telnet, cls.vnc]

    @classmethod
    def db_protocols(cls):
        return [
            cls.mysql, cls.mariadb, cls.postgresql, cls.oracle,
            cls.sqlserver, cls.redis, cls.mongodb,
        ]

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
            cls.https: 443
        }

