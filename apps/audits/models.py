# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _


class LoginLog(models.Model):
    LOGIN_TYPE_CHOICE = (
        ('S', 'ssh'),
        ('W', 'web'),
    )

    username = models.CharField(max_length=20, verbose_name=_('Username'))
    name = models.CharField(max_length=20, blank=True, verbose_name=_('Name'))
    login_type = models.CharField(choices=LOGIN_TYPE_CHOICE, max_length=1, verbose_name=_('Login type'))
    login_ip = models.GenericIPAddressField(verbose_name=_('Login ip'))
    login_city = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Login city'))
    user_agent = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('User agent'))
    date_login = models.DateTimeField(auto_now=True, verbose_name=_('Date login'))
    date_logout = models.DateTimeField(null=True, verbose_name=_('Date logout'))

    class Meta:
        db_table = 'login_log'
        ordering = ['-date_login', 'username']


class ProxyLog(models.Model):
    LOGIN_TYPE_CHOICE = (
        ('S', 'ssh'),
        ('W', 'web'),
    )

    username = models.CharField(max_length=20,  verbose_name=_('Username'))
    name = models.CharField(max_length=20, blank=True, verbose_name=_('Name'))
    hostname = models.CharField(max_length=128, blank=True, verbose_name=_('Hostname'))
    ip = models.GenericIPAddressField(max_length=32, verbose_name=_('IP'))
    system_user = models.CharField(max_length=20, verbose_name=_('System user'))
    login_type = models.CharField(choices=LOGIN_TYPE_CHOICE, max_length=1, verbose_name=_('Login type'))
    log_file = models.CharField(max_length=1000, blank=True, null=True)
    is_finished = models.BooleanField(default=False, verbose_name=_('Is finished'))
    date_start = models.DateTimeField(auto_now=True, verbose_name=_('Date start'))
    date_finished = models.DateTimeField(null=True, verbose_name=_('Date finished'))

    def __unicode__(self):
        return '%s-%s-%s-%s' % (self.username, self.hostname, self.system_user, self.id)

    class Meta:
        db_table = 'proxy_log'
        ordering = ['-date_start', 'username']


class CommandLog(models.Model):
    proxy_log = models.ForeignKey(ProxyLog, on_delete=models.CASCADE, related_name='command_log')
    command = models.CharField(max_length=1000, blank=True)
    output = models.TextField(blank=True)
    date_start = models.DateTimeField(null=True)
    date_finished = models.DateTimeField(null=True)

    def __unicode__(self):
        return '%s: %s' % (self.id, self.command)

    class Meta:
        db_table = 'command_log'
        ordering = ['-date_start', 'command']
