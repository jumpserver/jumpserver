# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _


class LoginLog(models.Model):
    LOGIN_TYPE_CHOICE = (
        ('W', 'Web'),
        ('ST', 'SSH Terminal'),
        ('WT', 'Web Terminal')
    )

    username = models.CharField(max_length=20, verbose_name=_('Username'))
    name = models.CharField(max_length=20, blank=True, verbose_name=_('Name'))
    login_type = models.CharField(choices=LOGIN_TYPE_CHOICE, max_length=2,
                                  verbose_name=_('Login type'))
    login_ip = models.GenericIPAddressField(verbose_name=_('Login ip'))
    login_city = models.CharField(max_length=254, blank=True, null=True,
                                  verbose_name=_('Login city'))
    user_agent = models.CharField(max_length=254, blank=True, null=True,
                                  verbose_name=_('User agent'))
    date_login = models.DateTimeField(auto_now_add=True,
                                      verbose_name=_('Date login'))

    class Meta:
        db_table = 'login_log'
        ordering = ['-date_login', 'username']


class ProxyLog(models.Model):
    LOGIN_TYPE_CHOICE = (
        ('ST', 'SSH Terminal'),
        ('WT', 'Web Terminal'),
    )

    user = models.CharField(max_length=32,  verbose_name=_('User'))
    asset = models.CharField(max_length=32, verbose_name=_('Asset'))
    system_user = models.CharField(max_length=32, verbose_name=_('System user'))
    login_type = models.CharField(
        choices=LOGIN_TYPE_CHOICE, max_length=2, blank=True,
        null=True, verbose_name=_('Login type'))
    terminal = models.CharField(
        max_length=32, blank=True, null=True, verbose_name=_('Terminal'))
    is_failed = models.BooleanField(
        default=False, verbose_name=_('Did connect failed'))
    is_finished = models.BooleanField(
        default=False, verbose_name=_('Is finished'))
    date_start = models.DateTimeField(
        auto_created=True, verbose_name=_('Date start'))
    date_finished = models.DateTimeField(
        null=True, verbose_name=_('Date finished'))

    def __unicode__(self):
        return '%s-%s-%s' % (self.user, self.asset, self.system_user)

    def commands(self):
        from audits.backends import command_store
        return command_store.filter(proxy_log_id=self.id)

    class Meta:
        ordering = ['-date_start', 'user']


class CommandLog(models.Model):
    proxy_log_id = models.IntegerField(db_index=True)
    user = models.CharField(max_length=48, db_index=True)
    asset = models.CharField(max_length=128, db_index=True)
    system_user = models.CharField(max_length=48, db_index=True)
    command_no = models.IntegerField()
    command = models.TextField(max_length=767, blank=True)
    output = models.TextField(blank=True)
    timestamp = models.FloatField(db_index=True)

    def __unicode__(self):
        return '%s: %s' % (self.id, self.command)

    class Meta:
        ordering = ['command_no', 'command']


class RecordLog(models.Model):
    proxy_log_id = models.IntegerField(db_index=True)
    output = models.TextField(verbose_name=_('Output'))
    timestamp = models.FloatField(db_index=True)

    def __unicode__(self):
        return 'Record: %s' % self.proxy_log_id

    class Meta:
        ordering = ['timestamp']
