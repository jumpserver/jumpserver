# -*- coding: utf-8 -*-
#

from __future__ import unicode_literals
import base64

from django.db import models
from django.utils.translation import ugettext_lazy as _


class LoginLog(models.Model):
    LOGIN_TYPE_CHOICE = (
        ('W', 'Web'),
        ('S', 'SSH Terminal'),
        ('WT', 'Web Terminal')
    )

    username = models.CharField(max_length=20, verbose_name=_('Username'))
    name = models.CharField(max_length=20, blank=True, verbose_name=_('Name'))
    login_type = models.CharField(choices=LOGIN_TYPE_CHOICE, max_length=2, verbose_name=_('Login type'))
    terminal = models.CharField(max_length=32, verbose_name=_('Terminal'))
    login_ip = models.GenericIPAddressField(verbose_name=_('Login ip'))
    login_city = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('Login city'))
    user_agent = models.CharField(max_length=100, blank=True, null=True, verbose_name=_('User agent'))
    date_login = models.DateTimeField(auto_now_add=True, verbose_name=_('Date login'))

    class Meta:
        db_table = 'login_log'
        ordering = ['-date_login', 'username']


class ProxyLog(models.Model):
    LOGIN_TYPE_CHOICE = (
        ('S', 'SSH Terminal'),
        ('WT', 'Web Terminal'),
    )

    username = models.CharField(max_length=20,  verbose_name=_('Username'))
    name = models.CharField(max_length=20, blank=True, verbose_name=_('Name'))
    hostname = models.CharField(max_length=128, blank=True, verbose_name=_('Hostname'))
    ip = models.GenericIPAddressField(max_length=32, verbose_name=_('IP'))
    system_user = models.CharField(max_length=20, verbose_name=_('System user'))
    login_type = models.CharField(choices=LOGIN_TYPE_CHOICE, max_length=2, blank=True,
                                  null=True, verbose_name=_('Login type'))
    terminal = models.CharField(max_length=32, blank=True, null=True, verbose_name=_('Terminal'))
    log_file = models.CharField(max_length=1000, blank=True, null=True)
    was_failed = models.BooleanField(default=False, verbose_name=_('Did connect failed'))
    is_finished = models.BooleanField(default=False, verbose_name=_('Is finished'))
    date_start = models.DateTimeField(verbose_name=_('Date start'))
    date_finished = models.DateTimeField(null=True, verbose_name=_('Date finished'))

    def __unicode__(self):
        return '%s-%s-%s-%s' % (self.username, self.hostname, self.system_user, self.id)

    @property
    def commands_dict(self):
        commands = self.command_log.all()
        return [
                    {
                        "command_no": command.command_no,
                        "command": command.command,
                        "output": command.output_decode,
                        "datetime": command.datetime,
                    } for command in commands]

    class Meta:
        db_table = 'proxy_log'
        ordering = ['-date_start', 'username']


class CommandLog(models.Model):
    proxy_log = models.ForeignKey(ProxyLog, on_delete=models.CASCADE, related_name='commands')
    command_no = models.IntegerField()
    command = models.CharField(max_length=1000, blank=True)
    output = models.TextField(blank=True)
    datetime = models.DateTimeField(null=True)

    def __unicode__(self):
        return '%s: %s' % (self.id, self.command)

    @property
    def output_decode(self):
        try:
            return base64.b64decode(self.output).replace('\n', '<br />')
        except UnicodeDecodeError:
            return 'UnicodeDecodeError'

    class Meta:
        db_table = 'command_log'
        ordering = ['command_no', 'command']
