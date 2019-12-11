# coding: utf-8
# 

from django.db import models
from django.utils.translation import ugettext_lazy as _

from .base import BasePermission

__all__ = [
    'DatabaseAppPermission',
]


class DatabaseAppPermission(BasePermission):
    database_apps = models.ManyToManyField(
        'applications.DatabaseApp', related_name='granted_by_permissions',
        blank=True, verbose_name=_("DatabaseApp")
    )

    class Meta:
        unique_together = [('org_id', 'name')]
        verbose_name = _('DatabaseApp permission')
        ordering = ('name',)
