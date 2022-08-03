from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel


class Protocol(JMSBaseModel):
    name = models.CharField(max_length=32, verbose_name=_("Name"))
    port = models.IntegerField(verbose_name=_("Port"))


class ProtocolMixin:
    protocol: str

    class Protocol(models.TextChoices):
        ssh = 'ssh', 'SSH'
        rdp = 'rdp', 'RDP'
        telnet = 'telnet', 'Telnet'
        vnc = 'vnc', 'VNC'
        mysql = 'mysql', 'MySQL'
        oracle = 'oracle', 'Oracle'
        mariadb = 'mariadb', 'MariaDB'
        postgresql = 'postgresql', 'PostgreSQL'
        sqlserver = 'sqlserver', 'SQLServer'
        redis = 'redis', 'Redis'
        mongodb = 'mongodb', 'MongoDB'
        k8s = 'k8s', 'K8S'

    SUPPORT_PUSH_PROTOCOLS = [Protocol.ssh, Protocol.rdp]

    ASSET_CATEGORY_PROTOCOLS = [
        Protocol.ssh, Protocol.rdp, Protocol.telnet, Protocol.vnc
    ]
    APPLICATION_CATEGORY_REMOTE_APP_PROTOCOLS = [
        Protocol.rdp
    ]
    APPLICATION_CATEGORY_DB_PROTOCOLS = [
        Protocol.mysql, Protocol.mariadb, Protocol.oracle,
        Protocol.postgresql, Protocol.sqlserver,
        Protocol.redis, Protocol.mongodb
    ]
    APPLICATION_CATEGORY_CLOUD_PROTOCOLS = [
        Protocol.k8s
    ]
    APPLICATION_CATEGORY_PROTOCOLS = [
        *APPLICATION_CATEGORY_REMOTE_APP_PROTOCOLS,
        *APPLICATION_CATEGORY_DB_PROTOCOLS,
        *APPLICATION_CATEGORY_CLOUD_PROTOCOLS
    ]

    @property
    def is_protocol_support_push(self):
        return self.protocol in self.SUPPORT_PUSH_PROTOCOLS

    @classmethod
    def get_protocol_by_application_type(cls, app_type):
        from applications.const import AppType
        if app_type in cls.APPLICATION_CATEGORY_PROTOCOLS:
            protocol = app_type
        elif app_type in AppType.remote_app_types():
            protocol = cls.Protocol.rdp
        else:
            protocol = None
        return protocol

    @property
    def can_perm_to_asset(self):
        return self.protocol in self.ASSET_CATEGORY_PROTOCOLS

    @property
    def is_asset_protocol(self):
        return self.protocol in self.ASSET_CATEGORY_PROTOCOLS

