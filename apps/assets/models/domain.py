# -*- coding: utf-8 -*-
#
import socket
import uuid
import random

from django.core.cache import cache
import paramiko
from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils import get_logger, lazyproperty
from orgs.mixins.models import OrgModelMixin
from .base import BaseUser

logger = get_logger(__file__)

__all__ = ['Domain', 'Gateway']


class Domain(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, verbose_name=_('Name'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    date_created = models.DateTimeField(auto_now_add=True, null=True,
                                        verbose_name=_('Date created'))

    class Meta:
        verbose_name = _("Domain")
        unique_together = [('org_id', 'name')]
        ordering = ('name',)

    def __str__(self):
        return self.name

    def has_gateway(self):
        return self.gateway_set.filter(is_active=True).exists()

    @lazyproperty
    def gateways(self):
        return self.gateway_set.filter(is_active=True)

    def random_gateway(self):
        gateways = [gw for gw in self.gateways if gw.is_connective]
        if gateways:
            return random.choice(gateways)

        logger.warn(f'Gateway all bad. domain={self}, gateway_num={len(self.gateways)}.')
        if self.gateways:
            return random.choice(self.gateways)


class Gateway(BaseUser):
    UNCONNECTIVE_KEY_TMPL = 'asset_unconnective_gateway_{}'
    UNCONNECTIVE_SILENCE_PERIOD_KEY_TMPL = 'asset_unconnective_gateway_silence_period_{}'
    UNCONNECTIVE_SILENCE_PERIOD_BEGIN_VALUE = 60 * 5

    class Protocol(models.TextChoices):
        ssh = 'ssh', 'SSH'

    ip = models.CharField(max_length=128, verbose_name=_('IP'), db_index=True)
    port = models.IntegerField(default=22, verbose_name=_('Port'))
    protocol = models.CharField(choices=Protocol.choices, max_length=16, default=Protocol.ssh, verbose_name=_("Protocol"))
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, verbose_name=_("Domain"))
    comment = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Comment"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))

    def __str__(self):
        return self.name

    class Meta:
        unique_together = [('name', 'org_id')]
        verbose_name = _("Gateway")
        permissions = [
            ('test_gateway', _('Test gateway'))
        ]

    def set_unconnective(self):
        unconnective_key = self.UNCONNECTIVE_KEY_TMPL.format(self.id)
        unconnective_silence_period_key = self.UNCONNECTIVE_SILENCE_PERIOD_KEY_TMPL.format(self.id)

        unconnective_silence_period = cache.get(unconnective_silence_period_key,
                                                self.UNCONNECTIVE_SILENCE_PERIOD_BEGIN_VALUE)
        cache.set(unconnective_silence_period_key, unconnective_silence_period * 2)
        cache.set(unconnective_key, unconnective_silence_period, unconnective_silence_period)

    def set_connective(self):
        unconnective_key = self.UNCONNECTIVE_KEY_TMPL.format(self.id)
        unconnective_silence_period_key = self.UNCONNECTIVE_SILENCE_PERIOD_KEY_TMPL.format(self.id)

        cache.delete(unconnective_key)
        cache.delete(unconnective_silence_period_key)

    def get_is_unconnective(self):
        unconnective_key = self.UNCONNECTIVE_KEY_TMPL.format(self.id)
        return cache.get(unconnective_key, False)

    @property
    def is_connective(self):
        return not self.get_is_unconnective()

    @is_connective.setter
    def is_connective(self, value):
        if value:
            self.set_connective()
        else:
            self.set_unconnective()

    def test_connective(self, local_port=None):
        if local_port is None:
            local_port = self.port

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        proxy = paramiko.SSHClient()
        proxy.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            proxy.connect(self.ip, port=self.port,
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
                err = _('Unable to connect to port {port} on {ip}')
                err = err.format(port=self.port, ip=self.ip)
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
                           key_filename=self.private_key_file,
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
