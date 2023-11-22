# -*- coding: utf-8 -*-
#
import random

from django.db import models
from django.utils.translation import gettext_lazy as _

from common.utils import get_logger
from labels.mixins import LabeledMixin
from orgs.mixins.models import JMSOrgBaseModel
from .gateway import Gateway

logger = get_logger(__file__)

__all__ = ['Domain']


class Domain(LabeledMixin, JMSOrgBaseModel):
    name = models.CharField(max_length=128, verbose_name=_('Name'))

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
        if not gateways:
            logger.warn(f'Not active gateway, domain={self}, pass')
            return None
        return random.choice(gateways)

    @property
    def active_gateways(self):
        return self.gateways.filter(is_active=True)

    @property
    def gateways(self):
        queryset = self.get_gateway_queryset().filter(domain=self)
        return queryset

    @classmethod
    def get_gateway_queryset(cls):
        return Gateway.objects.all()
