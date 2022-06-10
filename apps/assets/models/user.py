#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import logging

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.cache import cache

from common.utils import signer, get_object_or_none
from .base import BaseUser
from .asset import Asset
from .authbook import AuthBook


__all__ = ['AdminUser', 'SystemUser']
logger = logging.getLogger(__name__)


class ProtocolMixin:
    protocol: str

    class Protocol(models.TextChoices):
        ssh = 'ssh', 'SSH'
        rdp = 'rdp', 'RDP'
        telnet = 'telnet', 'Telnet'
        vnc = 'vnc', 'VNC'
        mysql = 'mysql', 'MySQL'
        oracle = 'oracle', 'Oracle'
        mariadb = 'mariadb', 'MariaDB'
        postgresql = 'postgresql', 'PostgreSQL'
        sqlserver = 'sqlserver', 'SQLServer'
        redis = 'redis', 'Redis'
        mongodb = 'mongodb', 'MongoDB'
        k8s = 'k8s', 'K8S'

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


class AuthMixin:
    username_same_with_user: bool
    protocol: str
    ASSET_CATEGORY_PROTOCOLS: list
    login_mode: str
    LOGIN_MANUAL: str
    id: str
    username: str
    password: str
    private_key: str
    public_key: str

    def set_temp_auth(self, asset_or_app_id, user_id, auth, ttl=300):
        if not auth:
            raise ValueError('Auth not set')
        key = 'TEMP_PASSWORD_{}_{}_{}'.format(self.id, asset_or_app_id, user_id)
        logger.debug(f'Set system user temp auth: {key}')
        cache.set(key, auth, ttl)

    def get_temp_auth(self, asset_or_app_id, user_id):
        key = 'TEMP_PASSWORD_{}_{}_{}'.format(self.id, asset_or_app_id, user_id)
        logger.debug(f'Get system user temp auth: {key}')
        password = cache.get(key)
        return password

    def _clean_auth_info_if_manual_login_mode(self):
        if self.login_mode == self.LOGIN_MANUAL:
            self.password = ''
            self.private_key = ''
            self.public_key = ''

    def _load_tmp_auth_if_has(self, asset_or_app_id, user_id):
        if self.login_mode != self.LOGIN_MANUAL:
            return

        if not asset_or_app_id or not user_id:
            return

        auth = self.get_temp_auth(asset_or_app_id, user_id)
        if not auth:
            return

        username = auth.get('username')
        password = auth.get('password')

        if username:
            self.username = username
        if password:
            self.password = password

    def load_app_more_auth(self, app_id=None, username=None, user_id=None):
        # 清除认证信息
        self._clean_auth_info_if_manual_login_mode()

        # 先加载临时认证信息
        if self.login_mode == self.LOGIN_MANUAL:
            self._load_tmp_auth_if_has(app_id, user_id)
            return

        # Remote app
        from applications.models import Application
        app = get_object_or_none(Application, pk=app_id)
        if app and app.category_remote_app:
            # Remote app
            self._load_remoteapp_more_auth(app, username, user_id)
            return

        # Other app
        # 更新用户名
        from users.models import User
        user = get_object_or_none(User, pk=user_id) if user_id else None
        if self.username_same_with_user:
            if user and not username:
                _username = user.username
            else:
                _username = username
            self.username = _username

    def _load_remoteapp_more_auth(self, app, username, user_id):
        asset = app.get_remote_app_asset(raise_exception=False)
        if asset:
            self.load_asset_more_auth(asset_id=asset.id, username=username, user_id=user_id)

    def load_asset_special_auth(self, asset, username=''):
        """
        AuthBook 的数据状态
            | asset | systemuser | username |
        1   |   *   |     *      |     x    |
        2   |   *   |     x      |     *    |

        当前 AuthBook 只有以上两种状态，systemuser 与 username 不会并存。
        正常的资产与系统用户关联产生的是第1种状态，改密则产生第2种状态。改密之后
        只有 username 而没有 systemuser 。

        Freq: 关联同一资产的多个系统用户指定同一用户名时，修改用户密码会影响所有系统用户

        这里有一个不对称的行为，同名系统用户密码覆盖
        当有相同 username 的多个系统用户时，有改密动作之后，所有的同名系统用户都使用最后
        一次改动，但如果没有发生过改密，同名系统用户使用的密码还是各自的。

        """
        if username == '':
            username = self.username

        authbook = AuthBook.objects.filter(
            asset=asset, username=username, systemuser__isnull=True
        ).order_by('-date_created').first()

        if not authbook:
            authbook = AuthBook.objects.filter(
                asset=asset, systemuser=self
            ).order_by('-date_created').first()

        if not authbook:
            return None

        authbook.load_auth()
        self.password = authbook.password
        self.private_key = authbook.private_key
        self.public_key = authbook.public_key

    def load_asset_more_auth(self, asset_id=None, username=None, user_id=None):
        from users.models import User
        self._clean_auth_info_if_manual_login_mode()
        # 加载临时认证信息
        if self.login_mode == self.LOGIN_MANUAL:
            self._load_tmp_auth_if_has(asset_id, user_id)
            return
        # 更新用户名
        user = get_object_or_none(User, pk=user_id) if user_id else None
        if self.username_same_with_user:
            if user and not username:
                _username = user.username
            else:
                _username = username
            self.username = _username
        # 加载某个资产的特殊配置认证信息
        asset = get_object_or_none(Asset, pk=asset_id) if asset_id else None
        if not asset:
            logger.debug('Asset not found, pass')
            return
        self.load_asset_special_auth(asset, self.username)


class SystemUser(ProtocolMixin, AuthMixin, BaseUser):
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
    nodes = models.ManyToManyField('assets.Node', blank=True, verbose_name=_("Nodes"))
    assets = models.ManyToManyField(
        'assets.Asset', blank=True, verbose_name=_("Assets"),
        through='assets.AuthBook', through_fields=['systemuser', 'asset'],
        related_name='system_users'
    )
    users = models.ManyToManyField('users.User', blank=True, verbose_name=_("Users"))
    groups = models.ManyToManyField('users.UserGroup', blank=True, verbose_name=_("User groups"))
    type = models.CharField(max_length=16, choices=Type.choices, default=Type.common, verbose_name=_('Type'))
    priority = models.IntegerField(default=81, verbose_name=_("Priority"), help_text=_("1-100, the lower the value will be match first"), validators=[MinValueValidator(1), MaxValueValidator(100)])
    protocol = models.CharField(max_length=16, choices=ProtocolMixin.Protocol.choices, default='ssh', verbose_name=_('Protocol'))
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
        if self.auto_push and self.is_protocol_support_push:
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
