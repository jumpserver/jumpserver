from django.db import models
from django.utils.translation import gettext_lazy as _


class Category(models.TextChoices):
    HOST = 'host', _('Host')
    NETWORK = 'network', _("Networking")
    DATABASE = 'database', _("Database")
    REMOTE_APP = 'remote_app', _("Remote app")
    CLOUD = 'cloud', _("Clouding")


class HostTypes(models.TextChoices):
    LINUX = 'linux', 'Linux'
    UNIX = 'unix', 'Unix'
    WINDOWS = 'windows', 'Windows'
    MACOS = 'macos', 'MacOS'
    MAINFRAME = 'mainframe', _("Mainframe")
    OTHER_HOST = 'other_host', _("Other host")

    def __new__(cls, value):
        """
        添加 Category
        :param value:
        """
        obj = str.__new__(cls)
        obj.category = Category.HOST
        return obj


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
    VSPHERE = 'vsphere', 'vSphere client'
    MYSQL_WORKBENCH = 'mysql_workbench', 'MySQL workbench'
    CUSTOM_REMOTE_APP = 'custom_remote_app', _("Custom")


class CloudTypes(models.TextChoices):
    K8S = 'k8s', 'Kubernetes'


class AllTypes:
    includes = [
        HostTypes, NetworkTypes, DatabaseTypes,
        RemoteAppTypes, CloudTypes
    ]

    @classmethod
    def choices(cls):
        choices = []
        for tp in cls.includes:
            choices.extend(tp.choices)
        return choices



