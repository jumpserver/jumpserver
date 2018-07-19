#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import uuid
from django.db import models
from django.utils.translation import ugettext_lazy as _
from rest_framework.authtoken.models import Token
from .user import User

__all__ = ['AccessKey', 'PrivateToken', 'LoginLog']


class AccessKey(models.Model):
    id = models.UUIDField(verbose_name='AccessKeyID', primary_key=True,
                          default=uuid.uuid4, editable=False)
    secret = models.UUIDField(verbose_name='AccessKeySecret',
                              default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, verbose_name='User',
                             on_delete=models.CASCADE, related_name='access_key')

    def get_id(self):
        return str(self.id)

    def get_secret(self):
        return str(self.secret)

    def __str__(self):
        return str(self.id)


class PrivateToken(Token):
    """Inherit from auth token, otherwise migration is boring"""

    class Meta:
        verbose_name = _('Private Token')


class LoginLog(models.Model):
    LOGIN_TYPE_CHOICE = (
        ('W', 'Web'),
        ('T', 'Terminal'),
    )

    MFA_DISABLED = 0
    MFA_ENABLED = 1
    MFA_UNKNOWN = 2

    MFA_CHOICE = (
        (MFA_DISABLED, _('Disabled')),
        (MFA_ENABLED, _('Enabled')),
        (MFA_UNKNOWN, _('-')),
    )

    REASON_NOTHING = 0
    REASON_PASSWORD = 1
    REASON_MFA = 2

    REASON_CHOICE = (
        (REASON_NOTHING, _('-')),
        (REASON_PASSWORD, _('Username/password check failed')),
        (REASON_MFA, _('MFA authentication failed')),
    )

    STATUS_CHOICE = (
        (True, _('Success')),
        (False, _('Failed'))
    )
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    username = models.CharField(max_length=20, verbose_name=_('Username'))
    type = models.CharField(choices=LOGIN_TYPE_CHOICE, max_length=2, verbose_name=_('Login type'))
    ip = models.GenericIPAddressField(verbose_name=_('Login ip'))
    city = models.CharField(max_length=254, blank=True, null=True, verbose_name=_('Login city'))
    user_agent = models.CharField(max_length=254, blank=True, null=True, verbose_name=_('User agent'))
    mfa = models.SmallIntegerField(default=MFA_UNKNOWN, choices=MFA_CHOICE, verbose_name=_('MFA'))
    reason = models.SmallIntegerField(default=REASON_NOTHING, choices=REASON_CHOICE, verbose_name=_('Reason'))
    status = models.BooleanField(max_length=2, default=True, choices=STATUS_CHOICE, verbose_name=_('Status'))
    datetime = models.DateTimeField(auto_now_add=True, verbose_name=_('Date login'))

    class Meta:
        ordering = ['-datetime', 'username']
