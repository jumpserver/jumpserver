#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _
from rest_framework.authtoken.models import Token
from . import User

__all__ = ['AccessKey', 'PrivateToken']


class AccessKey(models.Model):
    id = models.UUIDField(verbose_name='AccessKeyID', primary_key=True,
                          default=uuid.uuid4, editable=False)
    secret = models.UUIDField(verbose_name='AccessKeySecret',
                              default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, verbose_name='User',
                             related_name='access_key')

    def get_id(self):
        return str(self.id)

    def get_secret(self):
        return str(self.secret)

    def __unicode__(self):
        return str(self.id)

    __str__ = __unicode__


class PrivateToken(Token):
    """Inherit from auth token, otherwise migration is boring"""

    class Meta:
        verbose_name = _('Private Token')
