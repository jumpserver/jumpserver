#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import logging

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator

from .base import BaseAccount
from .protocol import ProtocolMixin


__all__ = ['SystemUser']
logger = logging.getLogger(__name__)


class SystemUser(ProtocolMixin, BaseAccount):
    LOGIN_AUTO = 'auto'
    LOGIN_MANUAL = 'manual'
    LOGIN_MODE_CHOICES = (
        (LOGIN_AUTO, _('Automatic managed')),
        (LOGIN_MANUAL, _('Manually input'))
    )

    class Type(models.TextChoices):
        common = 'common', _('Common user')
        admin = 'admin', _('Admin user')

    username_same_with_user = models.BooleanField(default=False, verbose_name=_("Username same with user"))
    type = models.CharField(max_length=16, choices=Type.choices, default=Type.common, verbose_name=_('Type'))
    priority = models.IntegerField(default=81, verbose_name=_("Priority"), help_text=_("1-100, the lower the value will be match first"), validators=[MinValueValidator(1), MaxValueValidator(100)])
    protocol = models.CharField(max_length=16, default='ssh', verbose_name=_('Protocol'))
    auto_push = models.BooleanField(default=True, verbose_name=_('Auto push'))
    sudo = models.TextField(default='/bin/whoami', verbose_name=_('Sudo'))
    shell = models.CharField(max_length=64,  default='/bin/bash', verbose_name=_('Shell'))
    login_mode = models.CharField(choices=LOGIN_MODE_CHOICES, default=LOGIN_AUTO, max_length=10, verbose_name=_('Login mode'))
    sftp_root = models.CharField(default='tmp', max_length=128, verbose_name=_("SFTP Root"))
    token = models.TextField(default='', verbose_name=_('Token'))
    home = models.CharField(max_length=4096, default='', verbose_name=_('Home'), blank=True)
    system_groups = models.CharField(default='', max_length=4096, verbose_name=_('System groups'), blank=True)
    ad_domain = models.CharField(default='', max_length=256)
    # linux su 命令 (switch user)
    su_enabled = models.BooleanField(default=False, verbose_name=_('User switch'))
    su_from = models.ForeignKey('self', on_delete=models.SET_NULL, related_name='su_to', null=True, verbose_name=_("Switch from"))

    class Meta:
        ordering = ['name']
        unique_together = [('name', 'org_id')]
        verbose_name = _("System user")
        permissions = [
            ('match_systemuser', _('Can match system user')),
        ]
