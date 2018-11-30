# -*- coding: utf-8 -*-
#
import uuid
import json

from django.db import models


class CommandExecution(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    pattern = models.CharField(max_length=64, default='all', verbose_name=_('Pattern'))
    _hosts = models.TextField(blank=True, verbose_name=_('Hosts'))  # ['hostid', 'hostid']
    run_as = models.CharField(max_length=128, default='', blank=True, verbose_name=_("Run as"))
    run_as_name = models.CharField(max_length=128, default='', blank=True)
    cmd = models.TextField(verbose_name=_("Command"))
    stdout = models.TextField(verbose_name=_("Output"))
    stderr = models.TextField(verbose_name=_("Error"))
    success = models.BooleanField(default=False)
    timedelta = models.IntegerField(default=0)
    user = models.CharField(verbose_name=_("User"))
    date_created = models.DateTimeField(auto_now_add=True)

    @property
    def hosts(self):
        return json.loads(self._hosts)

    @hosts.setter
    def hosts(self, item):
        self._hosts = json.dumps(item)

