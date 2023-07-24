# -*- coding: utf-8 -*-
#

from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from assets.const import Connectivity
from common.utils import (
    get_logger
)

logger = get_logger(__file__)


class AbsConnectivity(models.Model):
    connectivity = models.CharField(
        choices=Connectivity.choices, default=Connectivity.UNKNOWN,
        max_length=16, verbose_name=_('Connectivity')
    )
    date_verified = models.DateTimeField(null=True, verbose_name=_("Date verified"))

    def set_connectivity(self, val):
        self.connectivity = val
        self.date_verified = timezone.now()
        self.save(update_fields=['connectivity', 'date_verified'])

    @property
    def is_connective(self):
        if self.connectivity == Connectivity.OK:
            return True
        return False

    @classmethod
    def bulk_set_connectivity(cls, queryset_or_id, connectivity):
        if not isinstance(queryset_or_id, models.QuerySet):
            queryset = cls.objects.filter(id__in=queryset_or_id)
        else:
            queryset = queryset_or_id
        queryset.update(connectivity=connectivity, date_verified=timezone.now())

    class Meta:
        abstract = True
