# -*- coding: utf-8 -*-
#

from django.db import models
from django.utils.translation import ugettext as _

from .base import AssetUser
from orgs.mixins import OrgManager

__all__ = ['AuthBook']


class AuthBookQuerySet(models.QuerySet):

    def latest_version(self):
        return self.filter(is_latest=True)


class AuthBookManager(OrgManager):
    pass


class AuthBook(AssetUser):
    asset = models.ForeignKey('assets.Asset', on_delete=models.CASCADE, verbose_name=_('Asset'))
    is_latest = models.BooleanField(default=False, verbose_name=_('Latest'))
    version_count = models.IntegerField(default=1, verbose_name=_('Version count'))

    objects = AuthBookManager.from_queryset(AuthBookQuerySet)()

    class Meta:
        verbose_name = _('Auth book')

    @property
    def keyword(self):
        return {'username': self.username, 'asset': self.asset}

    def __str__(self):
        return '{}@{}'.format(self.username, self.asset)

