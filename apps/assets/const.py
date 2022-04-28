from django.db import models
from django.utils.translation import gettext_lazy as _
from common.db.models import IncludesTextChoicesMeta


__all__ = [
    'Category', 'HostTypes', 'NetworkTypes', 'DatabaseTypes',
    'RemoteAppTypes', 'CloudTypes', 'Protocol', 'AllTypes',
]


class Category(models.TextChoices):
    HOST = 'host', _('Host')
    NETWORK = 'network', _("NetworkDevice")
    DATABASE = 'database', _("Database")
    REMOTE_APP = 'remote_app', _("Remote app")
    CLOUD = 'cloud', _("Clouding")


class HostTypes(models.TextChoices):
    LINUX = 'linux', 'Linux'
    WINDOWS = 'windows', 'Windows'
    UNIX = 'unix', 'Unix'
    BSD = 'bsd', 'BSD'
    MACOS = 'macos', 'MacOS'
    MAINFRAME = 'mainframe', _("Mainframe")
    OTHER_HOST = 'other_host', _("Other host")


class NetworkTypes(models.TextChoices):
    SWITCH = 'switch', _("Switch")
    ROUTER = 'router', _("Router")
    FIREWALL = 'firewall', _("Firewall")
    OTHER_NETWORK = 'other_network', _("Other device")


class DatabaseTypes(models.TextChoices):
    MYSQL = 'mysql', 'MySQL'
    MARIADB = 'mariadb', 'MariaDB'
    POSTGRESQL = 'postgresql', 'PostgreSQL'
    ORACLE = 'oracle', 'Oracle'
    SQLSERVER = 'sqlserver', 'SQLServer'
    MONGODB = 'mongodb', 'MongoDB'
    REDIS = 'redis', 'Redis'


class RemoteAppTypes(models.TextChoices):
    CHROME = 'chrome', 'Chrome'
    VSPHERE = 'vmware_client', 'vSphere client'
    MYSQL_WORKBENCH = 'mysql_workbench', 'MySQL workbench'
    GENERAL_REMOTE_APP = 'general_remote_app', _("Custom")


class CloudTypes(models.TextChoices):
    K8S = 'k8s', 'Kubernetes'


class AllTypes(metaclass=IncludesTextChoicesMeta):
    choices: list
    includes = [
        HostTypes, NetworkTypes, DatabaseTypes,
        RemoteAppTypes, CloudTypes
    ]

    @classmethod
    def grouped_choices(cls):
        grouped_types= [
            (Category.HOST.value, HostTypes.choices),
            (Category.NETWORK.value, NetworkTypes.choices),
            (Category.DATABASE.value, DatabaseTypes.choices),
            (Category.REMOTE_APP.value, RemoteAppTypes.choices),
            (Category.CLOUD.value, CloudTypes.choices),
        ]
        return grouped_types

    @classmethod
    def grouped_choices_to_objs(cls):
        choices = cls.serialize_to_objs(Category.choices)
        mapper = dict(cls.grouped_choices())
        for choice in choices:
            children = cls.serialize_to_objs(mapper[choice['value']])
            choice['children'] = children
        return choices

    @staticmethod
    def serialize_to_objs(choices):
        title = ['value', 'display_name']
        return [dict(zip(title, choice)) for choice in choices]



class Protocol(models.TextChoices):
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

    @classmethod
    def host_protocols(cls):
        return [cls.ssh, cls.rdp, cls.telnet, cls.vnc]

    @classmethod
    def db_protocols(cls):
        return [
            cls.mysql, cls.mariadb, cls.postgresql, cls.oracle,
            cls.sqlserver, cls.redis, cls.mongodb,
        ]

