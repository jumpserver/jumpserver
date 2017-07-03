#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals

import logging

from django.db import models
from django.utils.translation import ugettext_lazy as _


__all__ = ['IDC']
logger = logging.getLogger(__name__)


class IDC(models.Model):
    name = models.CharField(max_length=32, verbose_name=_('Name'))
    bandwidth = models.CharField(
        max_length=32, blank=True, verbose_name=_('Bandwidth'))
    contact = models.CharField(
        max_length=128, blank=True, verbose_name=_('Contact'))
    phone = models.CharField(max_length=32, blank=True,
                             verbose_name=_('Phone'))
    address = models.CharField(
        max_length=128, blank=True, verbose_name=_("Address"))
    intranet = models.TextField(blank=True, verbose_name=_('Intranet'))
    extranet = models.TextField(blank=True, verbose_name=_('Extranet'))
    date_created = models.DateTimeField(
        auto_now_add=True, null=True, verbose_name=_('Date created'))
    operator = models.CharField(
        max_length=32, blank=True, verbose_name=_('Operator'))
    created_by = models.CharField(
        max_length=32, blank=True, verbose_name=_('Created by'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))

    def __unicode__(self):
        return self.name
    __str__ = __unicode__

    @classmethod
    def initial(cls):
        return cls.objects.get_or_create(name=_('Default'), created_by=_('System'), comment=_('Default IDC'))[0]

    class Meta:
        ordering = ['name']

    @classmethod
    def generate_fake(cls, count=5):
        from random import seed, choice
        import forgery_py
        from django.db import IntegrityError

        seed()
        for i in range(count):
            idc = cls(name=forgery_py.name.full_name(),
                      bandwidth='200M',
                      contact=forgery_py.name.full_name(),
                      phone=forgery_py.address.phone(),
                      address=forgery_py.address.city() + forgery_py.address.street_address(),
                      operator=choice(['北京联通', '北京电信', 'BGP全网通']),
                      comment=forgery_py.lorem_ipsum.sentence(),
                      created_by='Fake')
            try:
                idc.save()
                logger.debug('Generate fake asset group: %s' % idc.name)
            except IntegrityError:
                print('Error continue')
                continue
