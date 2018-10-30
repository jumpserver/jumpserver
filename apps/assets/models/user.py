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


__all__ = ['AdminUser', 'SystemUser',]
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
    SSH_PROTOCOL = 'ssh'
    RDP_PROTOCOL = 'rdp'
    TELNET_PROTOCOL = 'telnet'
    PROTOCOL_CHOICES = (
        (SSH_PROTOCOL, 'ssh'),
        (RDP_PROTOCOL, 'rdp'),
        (TELNET_PROTOCOL, 'telnet (beta)'),
    )

    AUTO_LOGIN = 'auto'
    MANUAL_LOGIN = 'manual'
    LOGIN_MODE_CHOICES = (
        (AUTO_LOGIN, _('Automatic login')),
        (MANUAL_LOGIN, _('Manually login'))
    )

    nodes = models.ManyToManyField('assets.Node', blank=True, verbose_name=_("Nodes"))
    assets = models.ManyToManyField('assets.Asset', blank=True, verbose_name=_("Assets"))
    priority = models.IntegerField(default=20, verbose_name=_("Priority"),
                                   validators=[MinValueValidator(1), MaxValueValidator(100)])
    protocol = models.CharField(max_length=16, choices=PROTOCOL_CHOICES, default='ssh', verbose_name=_('Protocol'))
    auto_push = models.BooleanField(default=True, verbose_name=_('Auto push'))
    sudo = models.TextField(default='/bin/whoami', verbose_name=_('Sudo'))
    shell = models.CharField(max_length=64,  default='/bin/bash', verbose_name=_('Shell'))
    login_mode = models.CharField(choices=LOGIN_MODE_CHOICES, default=AUTO_LOGIN, max_length=10, verbose_name=_('Login mode'))
    cmd_filters = models.ManyToManyField('CommandFilter', related_name='system_users', verbose_name=_("Command filter"), blank=True)

    cache_key = "__SYSTEM_USER_CACHED_{}"

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

    def get_assets(self):
        assets = set(self.assets.all())
        return assets

    @property
    def assets_connective(self):
        _result = cache.get(SYSTEM_USER_CONN_CACHE_KEY.format(self.name), {})
        return _result

    @property
    def unreachable_assets(self):
        return list(self.assets_connective.get('dark', {}).keys())

    @property
    def reachable_assets(self):
        return self.assets_connective.get('contacted', [])

    def is_need_push(self):
        if self.auto_push and self.protocol == self.__class__.SSH_PROTOCOL:
            return True
        else:
            return False

    def set_cache(self):
        cache.set(self.cache_key.format(self.id), self, 3600)

    def expire_cache(self):
        cache.delete(self.cache_key.format(self.id))

    @property
    def cmd_filter_rules(self):
        from .cmd_filter import CommandFilterRule
        rules = CommandFilterRule.objects.filter(
            filter__in=self.cmd_filters.all()
        ).distinct()
        return rules

    @classmethod
    def get_system_user_by_id_or_cached(cls, sid):
        cached = cache.get(cls.cache_key.format(sid))
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
