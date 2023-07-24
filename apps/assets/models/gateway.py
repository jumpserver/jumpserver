# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _

from assets.const import GATEWAY_NAME
from assets.models.platform import Platform
from common.utils import get_logger, lazyproperty
from orgs.mixins.models import OrgManager
from .asset.host import Host

logger = get_logger(__file__)

__all__ = ['Gateway']


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
        verbose_name = _("Gateway")

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

    @lazyproperty
    def username(self):
        account = self.select_account
        return account.username if account else None

    @lazyproperty
    def password(self):
        account = self.select_account
        return account.password if account else None

    @lazyproperty
    def port(self):
        protocol = self.protocols.filter(name='ssh').first()
        if protocol:
            return protocol.port
        else:
            return '22'

    @lazyproperty
    def private_key(self):
        account = self.select_account
        return account.private_key if account else None

    @lazyproperty
    def private_key_path(self):
        account = self.select_account
        return account.private_key_path if account else None
