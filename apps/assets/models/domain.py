# -*- coding: utf-8 -*-
#
import uuid
import random

import paramiko
from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils import get_logger, lazyproperty
from orgs.mixins.models import OrgModelMixin
from assets.models import Host
from assets.const import GATEWAY_NAME

logger = get_logger(__file__)

__all__ = ['Domain']


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

    @classmethod
    def get_gateway_queryset(cls):
        queryset = Host.objects.filter(
            platform__name=GATEWAY_NAME
        )
        return queryset

    @lazyproperty
    def gateways(self):
        return self.get_gateway_queryset().filter(domain=self, is_active=True)

    def select_gateway(self):
        return self.random_gateway()

    def random_gateway(self):
        gateways = [gw for gw in self.gateways if gw.is_connective]
        if gateways:
            return random.choice(gateways)

        logger.warn(f'Gateway all bad. domain={self}, gateway_num={len(self.gateways)}.')
        if self.gateways:
            return random.choice(self.gateways)


class Gateway(Host):
    class Meta:
        proxy = True

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
