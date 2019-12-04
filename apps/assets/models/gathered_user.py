# -*- coding: utf-8 -*-
#
import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _

from orgs.mixins.models import OrgModelMixin

__all__ = ['GatheredUser']


class GatheredUser(OrgModelMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, verbose_name=_("Asset"))
    username = models.CharField(max_length=32, blank=True, db_index=True, verbose_name=_('Username'))
    present = models.BooleanField(default=True, verbose_name=_("Present"))
    date_last_login = models.DateTimeField(null=True, verbose_name=_("Date last login"))
    ip_last_login = models.CharField(max_length=39, default='', verbose_name=_("IP last login"))
    date_created = models.DateTimeField(auto_now_add=True, verbose_name=_("Date created"))
    date_updated = models.DateTimeField(auto_now=True, verbose_name=_("Date updated"))

    @property
    def hostname(self):
        return self.asset.hostname

    @property
    def ip(self):
        return self.asset.ip

    class Meta:
        verbose_name = _('GatherUser')
        ordering = ['asset']

    def __str__(self):
        return '{}: {}'.format(self.asset.hostname, self.username)



