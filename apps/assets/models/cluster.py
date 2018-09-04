#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import logging
import uuid

from django.db import models
from django.utils.translation import ugettext_lazy as _


__all__ = ['Cluster']
logger = logging.getLogger(__name__)


class Cluster(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=32, verbose_name=_('Name'))
    admin_user = models.ForeignKey('assets.AdminUser', null=True, blank=True, on_delete=models.SET_NULL, verbose_name=_("Admin user"))
    bandwidth = models.CharField(max_length=32, blank=True, verbose_name=_('Bandwidth'))
    contact = models.CharField(max_length=128, blank=True, verbose_name=_('Contact'))
    phone = models.CharField(max_length=32, blank=True, verbose_name=_('Phone'))
    address = models.CharField(max_length=128, blank=True, verbose_name=_("Address"))
    intranet = models.TextField(blank=True, verbose_name=_('Intranet'))
    extranet = models.TextField(blank=True, verbose_name=_('Extranet'))
    date_created = models.DateTimeField(auto_now_add=True, null=True, verbose_name=_('Date created'))
    operator = models.CharField(max_length=32, blank=True, verbose_name=_('Operator'))
    created_by = models.CharField(max_length=32, blank=True, verbose_name=_('Created by'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return self.name

    @classmethod
    def initial(cls):
        return cls.objects.get_or_create(name=_('Default'), created_by=_('System'), comment=_('Default Cluster'))[0]

    class Meta:
        ordering = ['name']
        verbose_name = _("Cluster")

    @classmethod
    def generate_fake(cls, count=5):
        from random import seed, choice
        import forgery_py
        from django.db import IntegrityError

        seed()
        for i in range(count):
            cluster = cls(name=forgery_py.name.full_name(),
                          bandwidth='200M',
                          contact=forgery_py.name.full_name(),
                          phone=forgery_py.address.phone(),
                          address=forgery_py.address.city() + forgery_py.address.street_address(),
                          # operator=choice(['北京联通', '北京电信', 'BGP全网通']),
                          operator=choice([_('Beijing unicom'), _('Beijing telecom'), _('BGP full netcom')]),
                          comment=forgery_py.lorem_ipsum.sentence(),
                          created_by='Fake')
            try:
                cluster.save()
                logger.debug('Generate fake asset group: %s' % cluster.name)
            except IntegrityError:
                print('Error continue')
                continue
