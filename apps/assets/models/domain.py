# -*- coding: utf-8 -*-
#
import uuid
import random

import paramiko
from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils import get_logger, lazyproperty
from orgs.mixins.models import OrgModelMixin
from assets.models import Host, Platform
from assets.const import GATEWAY_NAME, SecretType
from orgs.mixins.models import OrgManager

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

    @classmethod
    def get_gateway_queryset(cls):
        return Gateway.objects.all()

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


class GatewayManager(OrgManager):
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(platform__name=GATEWAY_NAME)
        return queryset

    def bulk_create(self, objs, batch_size=None, ignore_conflicts=False):
        platform = Gateway().default_platform
        for obj in objs:
            obj.platform_id = platform.id
        return super().bulk_create(objs, batch_size, ignore_conflicts)


class Gateway(Host):
    objects = GatewayManager()

    class Meta:
        proxy = True

    @lazyproperty
    def default_platform(self):
        return Platform.objects.get(name=GATEWAY_NAME, internal=True)

    def save(self, *args, **kwargs):
        platform = self.default_platform
        self.platform_id = platform.id
        return super().save(*args, **kwargs)

    @lazyproperty
    def select_accounts(self) -> dict:
        account_dict = {}
        accounts = self.accounts.filter(is_active=True).order_by('-privileged', '-date_updated')
        password_account = accounts.filter(secret_type=SecretType.PASSWORD).first()
        if password_account:
            account_dict[SecretType.PASSWORD] = password_account

        ssh_key_account = accounts.filter(secret_type=SecretType.SSH_KEY).first()
        if ssh_key_account:
            account_dict[SecretType.SSH_KEY] = ssh_key_account
        return account_dict

    @property
    def password(self):
        account = self.select_accounts.get(SecretType.PASSWORD)
        return account.secret if account else None

    @property
    def private_key(self):
        account = self.select_accounts.get(SecretType.SSH_KEY)
        return account.secret if account else None

    def private_key_path(self):
        account = self.select_accounts.get(SecretType.SSH_KEY)
        return account.private_key_path if account else None

    @lazyproperty
    def username(self):
        accounts = self.select_accounts.values()
        if len(accounts) == 0:
            return None
        accounts = sorted(
            accounts, key=lambda x: x['privileged'], reverse=True
        )
        return accounts[0].username
