#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 

from __future__ import unicode_literals

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

__all__ = ['AssetGroup']


class AssetGroup(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    name = models.CharField(max_length=64, unique=True, verbose_name=_('Name'))
    created_by = models.CharField(max_length=32, null=True, blank=True, verbose_name=_('Created by'))
    date_created = models.DateTimeField(auto_now_add=True, null=True, verbose_name=_('Date created'))
    comment = models.TextField(blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = _("Asset group")

    @classmethod
    def initial(cls):
        asset_group = cls(name=_('Default'), comment=_('Default asset group'))
        asset_group.save()
