# -*- coding: utf-8 -*-
#

import uuid
import random

import paramiko

from django.db import models
from django.utils.translation import ugettext_lazy as _

from orgs.mixins import OrgModelMixin
from .base import AssetUser

__all__ = ['Domain', 'Gateway']


class Domain(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Name'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))
    date_created = models.DateTimeField(auto_now_add=True, null=True,
                                        verbose_name=_('Date created'))

    class Meta:
        verbose_name = _("Domain")

    def __str__(self):
        return self.name

    def has_gateway(self):
        return self.gateway_set.filter(is_active=True).exists()

    @property
    def gateways(self):
        return self.gateway_set.filter(is_active=True)

    def random_gateway(self):
        return random.choice(self.gateways)


class Gateway(AssetUser):
    PROTOCOL_SSH = 'ssh'
    PROTOCOL_RDP = 'rdp'
    PROTOCOL_CHOICES = (
        (PROTOCOL_SSH, 'ssh'),
        (PROTOCOL_RDP, 'rdp'),
    )
    ip = models.GenericIPAddressField(max_length=32, verbose_name=_('IP'), db_index=True)
    port = models.IntegerField(default=22, verbose_name=_('Port'))
    protocol = models.CharField(choices=PROTOCOL_CHOICES, max_length=16, default=PROTOCOL_SSH, verbose_name=_("Protocol"))
    domain = models.ForeignKey(Domain, on_delete=models.CASCADE, verbose_name=_("Domain"))
    comment = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Comment"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is active"))

    def __str__(self):
        return self.name

    class Meta:
        unique_together = [('name', 'org_id')]
        verbose_name = _("Gateway")

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
               paramiko.SSHException) as e:
            return False, str(e)

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
        except (paramiko.SSHException, paramiko.ssh_exception.SSHException,
                paramiko.AuthenticationException, TimeoutError) as e:
            return False, str(e)
        finally:
            client.close()
        return True, None
