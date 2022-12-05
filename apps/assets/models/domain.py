# -*- coding: utf-8 -*-
#
import uuid
import random
import socket
import paramiko

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils import get_logger, lazyproperty
from orgs.mixins.models import OrgManager
from orgs.mixins.models import OrgModelMixin

from ..models import Host, Platform
from ..const import GATEWAY_NAME, Connectivity

logger = get_logger(__file__)

__all__ = ['Domain', 'Gateway']


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

    def select_gateway(self):
        return self.random_gateway()

    def random_gateway(self):
        gateways = [gw for gw in self.active_gateways if gw.is_connective]
        if not gateways:
            gateways = self.active_gateways
            logger.warn(f'Gateway all bad. domain={self}, gateway_num={len(gateways)}.')
        return random.choice(gateways)

    @lazyproperty
    def active_gateways(self):
        return self.gateways.filter(is_active=True)

    @lazyproperty
    def gateways(self):
        return self.get_gateway_queryset().filter(domain=self)

    @classmethod
    def get_gateway_queryset(cls):
        return Gateway.objects.all()


class GatewayManager(OrgManager):
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(platform__name=GATEWAY_NAME)
        return queryset

    def bulk_create(self, objs, batch_size=None, ignore_conflicts=False):
        default_platform = Gateway.default_platform()
        for obj in objs:
            obj.platform = default_platform
        return super().bulk_create(objs, batch_size, ignore_conflicts)


class Gateway(Host):
    objects = GatewayManager()

    class Meta:
        proxy = True

    def save(self, *args, **kwargs):
        self.platform = self.default_platform()
        return super().save(*args, **kwargs)

    @classmethod
    def default_platform(cls):
        return Platform.objects.get(name=GATEWAY_NAME, internal=True)

    @lazyproperty
    def select_account(self):
        account = self.accounts.active().order_by('-privileged', '-date_updated').first()
        return account

    def test_connective(self, local_port=None):
        from ..models import Account

        local_port = self.port if local_port is None else local_port
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        proxy = paramiko.SSHClient()
        proxy.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if not isinstance(self.select_account, Account):
            err = _('No account')
            return False, err

        logger.debug('Test account: {}'.format(self.select_account))
        try:
            proxy.connect(
                self.address,
                port=self.port,
                username=self.select_account.username,
                password=self.select_account.secret,
                pkey=self.select_account.private_key_obj
            )
        except(
                paramiko.AuthenticationException,
                paramiko.BadAuthenticationType,
                paramiko.SSHException,
                paramiko.ChannelException,
                paramiko.ssh_exception.NoValidConnectionsError,
                socket.gaierror
        ) as e:
            err = str(e)
            if err.startswith('[Errno None] Unable to connect to port'):
                err = _('Unable to connect to port {port} on {address}')
                err = err.format(port=self.port, address=self.address)
            elif err == 'Authentication failed.':
                err = _('Authentication failed')
            elif err == 'Connect failed':
                err = _('Connect failed')
            self.set_connectivity(Connectivity.FAILED)
            return False, err

        try:
            sock = proxy.get_transport().open_channel(
                'direct-tcpip', ('127.0.0.1', local_port), ('127.0.0.1', 0)
            )
            client.connect(
                '127.0.0.1',
                sock=sock,
                timeout=5,
                port=local_port,
                username=self.username,
                password=self.password,
                key_filename=self.private_key_path,
            )
        except (
                paramiko.SSHException,
                paramiko.ssh_exception.SSHException,
                paramiko.ChannelException,
                paramiko.AuthenticationException,
                TimeoutError
        ) as e:

            err = getattr(e, 'text', str(e))
            if err == 'Connect failed':
                err = _('Connect failed')
            self.set_connectivity(Connectivity.FAILED)
            return False, err
        finally:
            client.close()
        self.set_connectivity(Connectivity.OK)
        return True, None
