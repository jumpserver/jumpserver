# -*- coding: utf-8 -*-
#
import uuid
import socket
import random
import paramiko

from django.db import models
from django.core.cache import cache
from django.db.models.query import QuerySet
from django.utils.translation import ugettext_lazy as _

from common.db import fields
from common.utils import get_logger, lazyproperty
from orgs.mixins.models import OrgModelMixin
from assets.models import Host
from .base import BaseAccount
from ..const import SecretType

logger = get_logger(__file__)

__all__ = ['Domain', 'GatewayMixin']


class Domain(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    date_created = models.DateTimeField(auto_now_add=True, null=True, verbose_name=_('Date created'))

    class Meta:
        verbose_name = _("Domain")
        unique_together = [('org_id', 'name')]
        ordering = ('name',)

    def __str__(self):
        return self.name

    @lazyproperty
    def gateways(self):
        return Host.get_gateway_queryset().filter(domain=self, is_active=True)

    def select_gateway(self):
        return self.random_gateway()

    def random_gateway(self):
        gateways = [gw for gw in self.gateways if gw.is_connective]
        if gateways:
            return random.choice(gateways)

        logger.warn(f'Gateway all bad. domain={self}, gateway_num={len(self.gateways)}.')
        if self.gateways:
            return random.choice(self.gateways)


class GatewayMixin:
    id: uuid.UUID
    port: int
    address: str
    accounts: QuerySet
    private_key_path: str
    private_key_obj: paramiko.RSAKey
    UNCONNECTED_KEY_TMPL = 'asset_unconnective_gateway_{}'
    UNCONNECTED_SILENCE_PERIOD_KEY_TMPL = 'asset_unconnective_gateway_silence_period_{}'
    UNCONNECTED_SILENCE_PERIOD_BEGIN_VALUE = 60 * 5

    def set_unconnected(self):
        unconnected_key = self.UNCONNECTED_KEY_TMPL.format(self.id)
        unconnected_silence_period_key = self.UNCONNECTED_SILENCE_PERIOD_KEY_TMPL.format(self.id)
        unconnected_silence_period = cache.get(
            unconnected_silence_period_key, self.UNCONNECTED_SILENCE_PERIOD_BEGIN_VALUE
        )
        cache.set(unconnected_silence_period_key, unconnected_silence_period * 2)
        cache.set(unconnected_key, unconnected_silence_period, unconnected_silence_period)

    def set_connective(self):
        unconnected_key = self.UNCONNECTED_KEY_TMPL.format(self.id)
        unconnected_silence_period_key = self.UNCONNECTED_SILENCE_PERIOD_KEY_TMPL.format(self.id)

        cache.delete(unconnected_key)
        cache.delete(unconnected_silence_period_key)

    def get_is_unconnected(self):
        unconnected_key = self.UNCONNECTED_KEY_TMPL.format(self.id)
        return cache.get(unconnected_key, False)

    @property
    def is_connective(self):
        return not self.get_is_unconnected()

    @is_connective.setter
    def is_connective(self, value):
        if value:
            self.set_connective()
        else:
            self.set_unconnected()

    def test_connective(self, local_port=None):
        # TODO 走ansible runner
        if local_port is None:
            local_port = self.port

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        proxy = paramiko.SSHClient()
        proxy.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            proxy.connect(self.address, port=self.port,
                          username=self.username,
                          password=self.password,
                          pkey=self.private_key_obj)
        except(paramiko.AuthenticationException,
               paramiko.BadAuthenticationType,
               paramiko.SSHException,
               paramiko.ChannelException,
               paramiko.ssh_exception.NoValidConnectionsError,
               socket.gaierror) as e:
            err = str(e)
            if err.startswith('[Errno None] Unable to connect to port'):
                err = _('Unable to connect to port {port} on {address}')
                err = err.format(port=self.port, ip=self.address)
            elif err == 'Authentication failed.':
                err = _('Authentication failed')
            elif err == 'Connect failed':
                err = _('Connect failed')
            self.is_connective = False
            return False, err

        try:
            sock = proxy.get_transport().open_channel(
                'direct-tcpip', ('127.0.0.1', local_port), ('127.0.0.1', 0)
            )
            client.connect("127.0.0.1", port=local_port,
                           username=self.username,
                           password=self.password,
                           key_filename=self.private_key_path,
                           sock=sock,
                           timeout=5)
        except (paramiko.SSHException,
                paramiko.ssh_exception.SSHException,
                paramiko.ChannelException,
                paramiko.AuthenticationException,
                TimeoutError) as e:

            err = getattr(e, 'text', str(e))
            if err == 'Connect failed':
                err = _('Connect failed')
            self.is_connective = False
            return False, err
        finally:
            client.close()
        self.is_connective = True
        return True, None

    @lazyproperty
    def username(self):
        account = self.accounts.all().first()
        if account:
            return account.username
        logger.error(f'Gateway {self} has no account')
        return ''

    def get_secret(self, secret_type):
        account = self.accounts.filter(secret_type=secret_type).first()
        if account:
            return account.secret
        logger.error(f'Gateway {self} has no {secret_type} account')

    @lazyproperty
    def password(self):
        secret_type = SecretType.PASSWORD
        return self.get_secret(secret_type)

    @lazyproperty
    def private_key(self):
        secret_type = SecretType.SSH_KEY
        return self.get_secret(secret_type)


class Gateway(BaseAccount):
    class Protocol(models.TextChoices):
        ssh = 'ssh', 'SSH'

    name = models.CharField(max_length=128, verbose_name='Name')
    ip = models.CharField(max_length=128, verbose_name=_('IP'), db_index=True)
    port = models.IntegerField(default=22, verbose_name=_('Port'))
    protocol = models.CharField(
        choices=Protocol.choices, max_length=16, default=Protocol.ssh, verbose_name=_("Protocol")
    )
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, verbose_name=_("Domain"))
    comment = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Comment"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))
    password = fields.EncryptCharField(max_length=256, blank=True, null=True, verbose_name=_('Password'))
    private_key = fields.EncryptTextField(blank=True, null=True, verbose_name=_('SSH private key'))
    public_key = fields.EncryptTextField(blank=True, null=True, verbose_name=_('SSH public key'))

    secret = None
    secret_type = None
    privileged = None

    def __str__(self):
        return self.name

    class Meta:
        unique_together = [('name', 'org_id')]
        verbose_name = _("Gateway")
        permissions = [
            ('test_gateway', _('Test gateway'))
        ]
