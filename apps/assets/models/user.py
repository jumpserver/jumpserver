#!/usr/bin/env python
# -*- coding: utf-8 -*-
#

import logging

from django.core.cache import cache
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator

from common.utils import get_signer
from ..const import SYSTEM_USER_CONN_CACHE_KEY
from .base import AssetUser


__all__ = ['AdminUser', 'SystemUser']
logger = logging.getLogger(__name__)
signer = get_signer()


class AdminUser(AssetUser):
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
    _become_pass = models.CharField(default='', max_length=128)
    CONNECTIVE_CACHE_KEY = '_JMS_ADMIN_USER_CONNECTIVE_{}'

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

    def get_related_assets(self):
        assets = self.asset_set.all()
        return assets

    @property
    def assets_amount(self):
        return self.get_related_assets().count()

    @property
    def connectivity(self):
        from .asset import Asset
        assets = self.get_related_assets().values_list('id', 'hostname', flat=True)
        data = {
            'unreachable': [],
            'reachable': [],
        }
        for asset_id, hostname in assets:
            key = Asset.CONNECTIVITY_CACHE_KEY.format(str(self.id))
            value = cache.get(key, Asset.UNKNOWN)
            if value == Asset.REACHABLE:
                data['reachable'].append(hostname)
            elif value == Asset.UNREACHABLE:
                data['unreachable'].append(hostname)
        return data

    class Meta:
        ordering = ['name']
        unique_together = [('name', 'org_id')]
        verbose_name = _("Admin user")

    @classmethod
    def generate_fake(cls, count=10):
        from random import seed
        import forgery_py
        from django.db import IntegrityError

        seed()
        for i in range(count):
            obj = cls(name=forgery_py.name.full_name(),
                      username=forgery_py.internet.user_name(),
                      password=forgery_py.lorem_ipsum.word(),
                      comment=forgery_py.lorem_ipsum.sentence(),
                      created_by='Fake')
            try:
                obj.save()
                logger.debug('Generate fake asset group: %s' % obj.name)
            except IntegrityError:
                print('Error continue')
                continue


class SystemUser(AssetUser):
    PROTOCOL_SSH = 'ssh'
    PROTOCOL_RDP = 'rdp'
    PROTOCOL_TELNET = 'telnet'
    PROTOCOL_VNC = 'vnc'
    PROTOCOL_CHOICES = (
        (PROTOCOL_SSH, 'ssh'),
        (PROTOCOL_RDP, 'rdp'),
        (PROTOCOL_TELNET, 'telnet (beta)'),
        (PROTOCOL_VNC, 'vnc'),
    )

    LOGIN_AUTO = 'auto'
    LOGIN_MANUAL = 'manual'
    LOGIN_MODE_CHOICES = (
        (LOGIN_AUTO, _('Automatic login')),
        (LOGIN_MANUAL, _('Manually login'))
    )

    nodes = models.ManyToManyField('assets.Node', blank=True, verbose_name=_("Nodes"))
    assets = models.ManyToManyField('assets.Asset', blank=True, verbose_name=_("Assets"))
    priority = models.IntegerField(default=20, verbose_name=_("Priority"), validators=[MinValueValidator(1), MaxValueValidator(100)])
    protocol = models.CharField(max_length=16, choices=PROTOCOL_CHOICES, default='ssh', verbose_name=_('Protocol'))
    auto_push = models.BooleanField(default=True, verbose_name=_('Auto push'))
    sudo = models.TextField(default='/bin/whoami', verbose_name=_('Sudo'))
    shell = models.CharField(max_length=64,  default='/bin/bash', verbose_name=_('Shell'))
    login_mode = models.CharField(choices=LOGIN_MODE_CHOICES, default=LOGIN_AUTO, max_length=10, verbose_name=_('Login mode'))
    cmd_filters = models.ManyToManyField('CommandFilter', related_name='system_users', verbose_name=_("Command filter"), blank=True)

    SYSTEM_USER_CACHE_KEY = "__SYSTEM_USER_CACHED_{}"
    CONNECTIVE_CACHE_KEY = '_JMS_SYSTEM_USER_CONNECTIVE_{}'

    def __str__(self):
        return '{0.name}({0.username})'.format(self)

    def to_json(self):
        return {
            'id': self.id,
            'name': self.name,
            'username': self.username,
            'protocol': self.protocol,
            'priority': self.priority,
            'auto_push': self.auto_push,
        }

    def get_related_assets(self):
        assets = set(self.assets.all())
        return assets

    @property
    def connectivity(self):
        cache_key = self.CONNECTIVE_CACHE_KEY.format(str(self.id))
        value = cache.get(cache_key, None)
        if not value or 'unreachable' not in value:
            return {'unreachable': [], 'reachable': []}
        else:
            return value

    @connectivity.setter
    def connectivity(self, value):
        data = self.connectivity
        unreachable = data['unreachable']
        reachable = data['reachable']

        for host in value.get('dark', {}).keys():
            if host not in unreachable:
                unreachable.append(host)
            if host in reachable:
                reachable.remove(host)
        for host in value.get('contacted'):
            if host not in reachable:
                reachable.append(host)
            if host in unreachable:
                unreachable.remove(host)
        cache_key = self.CONNECTIVE_CACHE_KEY.format(str(self.id))
        cache.set(cache_key, data, 3600)

    @property
    def assets_unreachable(self):
        return self.connectivity.get('unreachable')

    @property
    def assets_reachable(self):
        return self.connectivity.get('reachable')

    @property
    def login_mode_display(self):
        return self.get_login_mode_display()

    def is_need_push(self):
        if self.auto_push and self.protocol == self.PROTOCOL_SSH:
            return True
        else:
            return False

    def set_cache(self):
        cache.set(self.SYSTEM_USER_CACHE_KEY.format(self.id), self, 3600)

    def expire_cache(self):
        cache.delete(self.SYSTEM_USER_CACHE_KEY.format(self.id))

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
            if action == rule.ACTION_ALLOW:
                return True, None
            elif action == rule.ACTION_DENY:
                return False, matched_cmd
        return True, None

    @classmethod
    def get_system_user_by_id_or_cached(cls, sid):
        cached = cache.get(cls.SYSTEM_USER_CACHE_KEY.format(sid))
        if cached:
            return cached
        try:
            system_user = cls.objects.get(id=sid)
            system_user.set_cache()
            return system_user
        except cls.DoesNotExist:
            return None

    class Meta:
        ordering = ['name']
        unique_together = [('name', 'org_id')]
        verbose_name = _("System user")

    @classmethod
    def generate_fake(cls, count=10):
        from random import seed
        import forgery_py
        from django.db import IntegrityError

        seed()
        for i in range(count):
            obj = cls(name=forgery_py.name.full_name(),
                      username=forgery_py.internet.user_name(),
                      password=forgery_py.lorem_ipsum.word(),
                      comment=forgery_py.lorem_ipsum.sentence(),
                      created_by='Fake')
            try:
                obj.save()
                logger.debug('Generate fake asset group: %s' % obj.name)
            except IntegrityError:
                print('Error continue')
                continue
