#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import logging

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator

from assets.const import Protocol
from common.utils import signer
from .base import BaseUser
from .asset import Asset


__all__ = ['AdminUser', 'SystemUser', 'ProtocolMixin']
logger = logging.getLogger(__name__)


class ProtocolMixin:
    protocol: str
    Protocol = Protocol

    SUPPORT_PUSH_PROTOCOLS = [Protocol.ssh, Protocol.rdp]

    ASSET_CATEGORY_PROTOCOLS = [
        Protocol.ssh, Protocol.rdp, Protocol.telnet, Protocol.vnc
    ]
    APPLICATION_CATEGORY_REMOTE_APP_PROTOCOLS = [
        Protocol.rdp
    ]
    APPLICATION_CATEGORY_DB_PROTOCOLS = [
        Protocol.mysql, Protocol.mariadb, Protocol.oracle,
        Protocol.postgresql, Protocol.sqlserver,
        Protocol.redis, Protocol.mongodb
    ]
    APPLICATION_CATEGORY_CLOUD_PROTOCOLS = [
        Protocol.k8s
    ]
    APPLICATION_CATEGORY_PROTOCOLS = [
        *APPLICATION_CATEGORY_REMOTE_APP_PROTOCOLS,
        *APPLICATION_CATEGORY_DB_PROTOCOLS,
        *APPLICATION_CATEGORY_CLOUD_PROTOCOLS
    ]

    @property
    def is_protocol_support_push(self):
        return self.protocol in self.SUPPORT_PUSH_PROTOCOLS

    @classmethod
    def get_protocol_by_application_type(cls, app_type):
        from applications.const import AppType
        if app_type in cls.APPLICATION_CATEGORY_PROTOCOLS:
            protocol = app_type
        elif app_type in AppType.remote_app_types():
            protocol = cls.Protocol.rdp
        else:
            protocol = None
        return protocol

    @property
    def can_perm_to_asset(self):
        return self.protocol in self.ASSET_CATEGORY_PROTOCOLS

    @property
    def is_asset_protocol(self):
        return self.protocol in self.ASSET_CATEGORY_PROTOCOLS


class SystemUser(ProtocolMixin, BaseUser):
    LOGIN_AUTO = 'auto'
    LOGIN_MANUAL = 'manual'
    LOGIN_MODE_CHOICES = (
        (LOGIN_AUTO, _('使用账号')),
        (LOGIN_MANUAL, _('Manually input'))
    )

    class Type(models.TextChoices):
        common = 'common', _('Common user')
        admin = 'admin', _('Admin user')

    username_same_with_user = models.BooleanField(default=False, verbose_name=_("Username same with user"))
    nodes = models.ManyToManyField('assets.Node', blank=True, verbose_name=_("Nodes"))
    assets = models.ManyToManyField(
        'assets.Asset', blank=True, verbose_name=_("Assets"),
        related_name='system_users'
    )
    users = models.ManyToManyField('users.User', blank=True, verbose_name=_("Users"))
    groups = models.ManyToManyField('users.UserGroup', blank=True, verbose_name=_("User groups"))
    priority = models.IntegerField(
        default=81, verbose_name=_("Priority"),
        help_text=_("1-100, the lower the value will be match first"),
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    protocol = models.CharField(max_length=16, choices=Protocol.choices, default='ssh', verbose_name=_('Protocol'))
    login_mode = models.CharField(choices=LOGIN_MODE_CHOICES, default=LOGIN_AUTO, max_length=10, verbose_name=_('Login mode'))

    # Todo: 重构平台后或许这里也得变化
    # 账号模版
    account_template_enabled = models.BooleanField(default=False, verbose_name=_("启用账号模版"))
    auto_push_account = models.BooleanField(default=True, verbose_name=_('自动推送账号'))
    type = models.CharField(max_length=16, choices=Type.choices, default=Type.common, verbose_name=_('Type'))
    auto_push = models.BooleanField(default=True, verbose_name=_('Auto push'))
    sudo = models.TextField(default='/bin/whoami', verbose_name=_('Sudo'))
    shell = models.CharField(max_length=64,  default='/bin/bash', verbose_name=_('Shell'))
    sftp_root = models.CharField(default='tmp', max_length=128, verbose_name=_("SFTP Root"))
    token = models.TextField(default='', verbose_name=_('Token'))
    home = models.CharField(max_length=4096, default='', verbose_name=_('Home'), blank=True)
    system_groups = models.CharField(default='', max_length=4096, verbose_name=_('System groups'), blank=True)
    ad_domain = models.CharField(default='', max_length=256)

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
    def nodes_amount(self):
        return self.nodes.all().count()

    @property
    def login_mode_display(self):
        return self.get_login_mode_display()

    def is_need_push(self):
        if self.auto_push_account and self.is_protocol_support_push:
            return True
        else:
            return False

    @property
    def is_admin_user(self):
        return self.type == self.Type.admin

    @property
    def is_need_cmd_filter(self):
        return self.protocol not in [self.Protocol.rdp, self.Protocol.vnc]

    @property
    def is_need_test_asset_connective(self):
        return self.protocol in self.ASSET_CATEGORY_PROTOCOLS

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

    def get_all_assets(self):
        from assets.models import Node
        nodes_keys = self.nodes.all().values_list('key', flat=True)
        asset_ids = set(self.assets.all().values_list('id', flat=True))
        nodes_asset_ids = Node.get_nodes_all_asset_ids_by_keys(nodes_keys)
        asset_ids.update(nodes_asset_ids)
        assets = Asset.objects.filter(id__in=asset_ids)
        return assets

    def add_related_assets(self, assets_or_ids):
        self.assets.add(*tuple(assets_or_ids))
        self.add_related_assets_to_su_from_if_need(assets_or_ids)

    def add_related_assets_to_su_from_if_need(self, assets_or_ids):
        if self.protocol not in [self.Protocol.ssh.value]:
            return
        if not self.su_enabled:
            return
        if not self.su_from:
            return
        if self.su_from.protocol != self.protocol:
            return
        self.su_from.assets.add(*tuple(assets_or_ids))

    class Meta:
        ordering = ['name']
        unique_together = [('name', 'org_id')]
        verbose_name = _("System user")
        permissions = [
            ('match_systemuser', _('Can match system user')),
        ]


# Deprecated: 准备废弃
class AdminUser(BaseUser):
    """
    A privileged user that ansible can use it to push system user and so on
    """
    BECOME_METHOD_CHOICES = (
        ('sudo', 'sudo'),
        ('su', 'su'),
    )
    become = models.BooleanField(default=True)
    become_method = models.CharField(choices=BECOME_METHOD_CHOICES, default='sudo', max_length=4)
    become_user = models.CharField(default='root', max_length=64)
    _become_pass = models.CharField(default='', blank=True, max_length=128)
    CONNECTIVITY_CACHE_KEY = '_ADMIN_USER_CONNECTIVE_{}'
    _prefer = "admin_user"

    def __str__(self):
        return self.name

    @property
    def become_pass(self):
        password = signer.unsign(self._become_pass)
        if password:
            return password
        else:
            return ""

    @become_pass.setter
    def become_pass(self, password):
        self._become_pass = signer.sign(password)

    @property
    def become_info(self):
        if self.become:
            info = {
                "method": self.become_method,
                "user": self.become_user,
                "pass": self.become_pass,
            }
        else:
            info = None
        return info

    class Meta:
        ordering = ['name']
        unique_together = [('name', 'org_id')]
        verbose_name = _("Admin user")
