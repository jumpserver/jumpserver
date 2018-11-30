# -*- coding: utf-8 -*-
#
import uuid
from django.db import models


class CommandExecution(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    pattern = models.CharField(max_length=64, default='all', verbose_name=_('Pattern'))
    _hosts = models.TextField(blank=True, verbose_name=_('Hosts'))  # ['hostname1', 'hostname2']
    run_as = models.CharField(max_length=128, default='', verbose_name=_("Run as"))
