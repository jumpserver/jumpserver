#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import logging

from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.cache import cache

from common.utils import signer, get_object_or_none
from common.db.models import ChoiceSet
from .base import BaseUser
from .asset import Asset
from .authbook import AuthBook


__all__ = ['AdminUser', 'SystemUser']
logger = logging.getLogger(__name__)


# Todo: 准备废弃
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


class ProtocolMixin:
    protocol: str

    PROTOCOL_SSH = 'ssh'
    PROTOCOL_RDP = 'rdp'
    PROTOCOL_TELNET = 'telnet'
    PROTOCOL_VNC = 'vnc'
    PROTOCOL_MYSQL = 'mysql'
    PROTOCOL_ORACLE = 'oracle'
    PROTOCOL_MARIADB = 'mariadb'
    PROTOCOL_POSTGRESQL = 'postgresql'
    PROTOCOL_K8S = 'k8s'
    PROTOCOL_CHOICES = (
        (PROTOCOL_SSH, 'ssh'),
        (PROTOCOL_RDP, 'rdp'),
        (PROTOCOL_TELNET, 'telnet'),
        (PROTOCOL_VNC, 'vnc'),
        (PROTOCOL_MYSQL, 'mysql'),
        (PROTOCOL_ORACLE, 'oracle'),
        (PROTOCOL_MARIADB, 'mariadb'),
        (PROTOCOL_POSTGRESQL, 'postgresql'),
        (PROTOCOL_K8S, 'k8s'),
    )

    SUPPORT_PUSH_PROTOCOLS = [PROTOCOL_SSH, PROTOCOL_RDP]

    ASSET_CATEGORY_PROTOCOLS = [
        PROTOCOL_SSH, PROTOCOL_RDP, PROTOCOL_TELNET, PROTOCOL_VNC
    ]
    APPLICATION_CATEGORY_REMOTE_APP_PROTOCOLS = [
        PROTOCOL_RDP
    ]
    APPLICATION_CATEGORY_DB_PROTOCOLS = [
        PROTOCOL_MYSQL, PROTOCOL_ORACLE, PROTOCOL_MARIADB, PROTOCOL_POSTGRESQL
    ]
    APPLICATION_CATEGORY_CLOUD_PROTOCOLS = [
        PROTOCOL_K8S
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
        from applications.const import ApplicationTypeChoices
        if app_type in cls.APPLICATION_CATEGORY_PROTOCOLS:
            protocol = app_type
        elif app_type in ApplicationTypeChoices.remote_app_types():
            protocol = cls.PROTOCOL_RDP
        else:
            protocol = None
        return protocol

    @property
    def can_perm_to_asset(self):
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

    def load_tmp_auth_if_has(self, asset_or_app_id, user):
        if not asset_or_app_id or not user:
            return
        if self.login_mode != self.LOGIN_MANUAL:
            pass

        auth = self.get_temp_auth(asset_or_app_id, user)
        if not auth:
            return
        username = auth.get('username')
        password = auth.get('password')

        if username:
            self.username = username
        if password:
            self.password = password

    def load_app_more_auth(self, app_id=None, user_id=None):
        from users.models import User

        if self.login_mode == self.LOGIN_MANUAL:
            self.password = ''
            self.private_key = ''
        if not user_id:
            return
        user = get_object_or_none(User, pk=user_id)
        if not user:
            return
        self.load_tmp_auth_if_has(app_id, user)

    def load_asset_special_auth(self, asset, username=''):
        """
        有用户名，代表手动设置过密码，给 4分
        有资产: 代表为某个资产设置过，给 2分
        有系统用户: 给 1分
        """
        system_user = self
        # 1: 优先匹配，有用户名, 有系统用户，有资产的，得分 7
        q1 = Q(asset=asset, system_user=system_user, username=username)
        # 2: 第二优先级, 有资产，有用户名的, 这个是可能从修改密码过来的，或者单独设置的, 得分 6
        q2 = Q(asset=asset, username=username)
        # 3: 这个可能是动态系统用户，为某个用户单独设置的密码, 得分 5
        q3 = Q(username=username, system_user=system_user)
        # 4: 系统用户自己的默认账号密码, 得分 3
        q4 = Q(asset=asset, system_user=system_user),

        def sort_auth(authbook):
            score = 0
            if authbook.password or authbook.private_key:
                score += 4
            if authbook.asset:
                score += 2
            if authbook.system_user:
                score += 1
            return score
        authbooks = list(AuthBook.objects.filter(q1 | q2 | q3 | q4))
        authbooks = sorted(authbooks, key=sort_auth, reverse=True)
        if len(authbooks) == 0:
            return None

        if username:
            self.username = username

        password_set, key_set = False
        for auth in authbooks:
            if auth.password and not password_set:
                self.password = auth.password
                password_set = True
            if auth.private_key and not key_set:
                self.private_key = auth.private_key
                self.public_key = auth.public_key
            if password_set and key_set:
                break

    def load_asset_more_auth(self, asset_id=None, username=None, user_id=None):
        from users.models import User

        if self.login_mode == self.LOGIN_MANUAL:
            self.password = ''
            self.private_key = ''

        asset = None
        if asset_id:
            asset = get_object_or_none(Asset, pk=asset_id)
        # 没有资产就没有必要继续了
        if not asset:
            logger.debug('Asset not found, pass')
            return

        user = None
        if user_id:
            user = get_object_or_none(User, pk=user_id)

        if self.username_same_with_user and not username and user:
            username = user.username

        # 加载某个资产的特殊配置认证信息
        try:
            self.load_asset_special_auth(asset, username)
        except Exception as e:
            logger.error('Load special auth Error: ', e)
            pass

        self.load_tmp_auth_if_has(asset_id, user)


class SystemUser(ProtocolMixin, BaseUser):
    LOGIN_AUTO = 'auto'
    LOGIN_MANUAL = 'manual'
    LOGIN_MODE_CHOICES = (
        (LOGIN_AUTO, _('Automatic login')),
        (LOGIN_MANUAL, _('Manually login'))
    )

    class Type(ChoiceSet):
        common = 'common', _('Common user')
        admin = 'admin', _('Admin user')
        dynamic = 'dynamic', _('Dynamic user')

    username_same_with_user = models.BooleanField(default=False, verbose_name=_("Username same with user"))
    nodes = models.ManyToManyField('assets.Node', blank=True, verbose_name=_("Nodes"))
    assets = models.ManyToManyField(
        'assets.Asset', blank=True, verbose_name=_("Assets"),
        through='assets.AuthBook', through_fields=['system_user', 'asset']
    )
    users = models.ManyToManyField('users.User', blank=True, verbose_name=_("Users"))
    groups = models.ManyToManyField('users.UserGroup', blank=True, verbose_name=_("User groups"))
    type = models.CharField(max_length=16, choices=Type.choices, default=Type.common, verbose_name=_('Type'))
    priority = models.IntegerField(default=81, verbose_name=_("Priority"), help_text=_("1-100, the lower the value will be match first"), validators=[MinValueValidator(1), MaxValueValidator(100)])
    protocol = models.CharField(max_length=16, choices=ProtocolMixin.PROTOCOL_CHOICES, default='ssh', verbose_name=_('Protocol'))
    auto_push = models.BooleanField(default=True, verbose_name=_('Auto push'))
    sudo = models.TextField(default='/bin/whoami', verbose_name=_('Sudo'))
    shell = models.CharField(max_length=64,  default='/bin/bash', verbose_name=_('Shell'))
    login_mode = models.CharField(choices=LOGIN_MODE_CHOICES, default=LOGIN_AUTO, max_length=10, verbose_name=_('Login mode'))
    cmd_filters = models.ManyToManyField('CommandFilter', related_name='system_users', verbose_name=_("Command filter"), blank=True)
    sftp_root = models.CharField(default='tmp', max_length=128, verbose_name=_("SFTP Root"))
    token = models.TextField(default='', verbose_name=_('Token'))
    home = models.CharField(max_length=4096, default='', verbose_name=_('Home'), blank=True)
    system_groups = models.CharField(default='', max_length=4096, verbose_name=_('System groups'), blank=True)
    ad_domain = models.CharField(default='', max_length=256)
    _prefer = 'system_user'

    def __str__(self):
        username = self.username
        if self.username_same_with_user:
            username = 'dynamic'
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
    def is_need_cmd_filter(self):
        return self.protocol not in [self.PROTOCOL_RDP, self.PROTOCOL_VNC]

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

    def save(self, *args, **kwargs):
        if self.username_same_with_user:
            self.username = '*'
        return super().save(*args, **kwargs)

    class Meta:
        ordering = ['name']
        unique_together = [('name', 'org_id')]
        verbose_name = _("System user")
