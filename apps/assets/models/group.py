#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 

from __future__ import unicode_literals

from django.db import models
import logging
from django.utils.translation import ugettext_lazy as _

from . import SystemUser

__all__ = ['AssetGroup']
logger = logging.getLogger(__name__)


class AssetGroup(models.Model):
    name = models.CharField(max_length=64, unique=True, verbose_name=_('Name'))
    system_users = models.ManyToManyField(SystemUser, related_name='asset_groups', blank=True)
    created_by = models.CharField(max_length=32, blank=True, verbose_name=_('Created by'))
    date_created = models.DateTimeField(auto_now_add=True, null=True, verbose_name=_('Date created'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))

    def __unicode__(self):
        return self.name
    __str__ = __unicode__

    class Meta:
        ordering = ['name']

    @classmethod
    def initial(cls):
        asset_group = cls(name=_('Default'), comment=_('Default asset group'))
        asset_group.save()

    @classmethod
    def generate_fake(cls, count=100):
        from random import seed
        import forgery_py
        from django.db import IntegrityError

        seed()
        for i in range(count):
            group = cls(name=forgery_py.name.full_name(),
                        comment=forgery_py.lorem_ipsum.sentence(),
                        created_by='Fake')
            try:
                group.save()
                logger.debug('Generate fake asset group: %s' % group.name)
            except IntegrityError:
                print('Error continue')
                continue
