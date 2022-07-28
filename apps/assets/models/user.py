#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import logging

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.shortcuts import get_object_or_404
from django.core.cache import cache

from .base import BaseUser
from .protocol import ProtocolMixin


__all__ = ['SystemUser']
logger = logging.getLogger(__name__)


class SystemUser(ProtocolMixin, BaseUser):
    LOGIN_AUTO = 'auto'
    LOGIN_MANUAL = 'manual'
    LOGIN_MODE_CHOICES = (
        (LOGIN_AUTO, _('使用账号')),
        (LOGIN_MANUAL, _('Manually input'))
    )

    username_same_with_user = models.BooleanField(default=False, verbose_name=_("Username same with user"))
    protocol = models.CharField(max_length=16, choices=ProtocolMixin.Protocol.choices, default='ssh', verbose_name=_('Protocol'))
    login_mode = models.CharField(choices=LOGIN_MODE_CHOICES, default=LOGIN_AUTO, max_length=10, verbose_name=_('Login mode'))

    # linux su 命令 (switch user)
    # Todo: 修改为 username, 不必系统用户了
    su_enabled = models.BooleanField(default=False, verbose_name=_('User switch'))
    su_from = models.ForeignKey('self', on_delete=models.SET_NULL, related_name='su_to', null=True, verbose_name=_("Switch from"))

    def __str__(self):
        username = self.username
        if self.username_same_with_user:
            username = '*'
        return '{0.name}({1})'.format(self, username)

    @property
    def cmd_filter_rules(self):
        from .cmd_filter import CommandFilterRule
        rules = CommandFilterRule.objects.filter(
            filter__in=self.cmd_filters.all()
        ).distinct()
        return rules

    def is_command_can_run(self, command):
        for rule in self.cmd_filter_rules:
            action, matched_cmd = rule.match(command)
            if action == rule.ActionChoices.allow:
                return True, None
            elif action == rule.ActionChoices.deny:
                return False, matched_cmd
        return True, None

    @classmethod
    def create_accounts_with_assets(cls, asset_ids, system_user_ids):
        pass

    def get_manual_account(self, user_id, asset_id):
        cache_key = 'manual_account_{}_{}_{}'.format(self.id, user_id, asset_id)
        return cache.get(cache_key)

    def create_manual_account(self, user_id, asset_id, account, ttl=300):
        cache_key = 'manual_account_{}_{}_{}'.format(self.id, user_id, asset_id)
        cache.set(cache_key, account, ttl)

    def get_auto_account(self, user_id, asset_id):
        from .account import Account
        from users.models import User
        username = self.username
        if self.username_same_with_user:
            user = get_object_or_404(User, id=user_id)
            username = user.username
        return get_object_or_404(Account, asset_id=asset_id, username=username)

    def get_account(self, user_id, asset_id):
        if self.login_mode == self.LOGIN_MANUAL:
            return self.get_manual_account(user_id, asset_id)
        else:
            return self.get_auto_account(user_id, asset_id)

    class Meta:
        ordering = ['name']
        unique_together = [('name', 'org_id')]
        verbose_name = _("System user")
        permissions = [
            ('match_systemuser', _('Can match system user')),
        ]
