# -*- coding: utf-8 -*-
#
import uuid
import random

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.utils import get_logger, lazyproperty
from orgs.mixins.models import OrgModelMixin

from .gateway import Gateway

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


