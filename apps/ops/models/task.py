# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals, absolute_import

import logging

from uuid import uuid4
from assets.models import Asset
from ops.models import TaskRecord

from django.db import models
from django.utils.translation import ugettext_lazy as _

__all__ = ["Task"]


class Task(models.Model):
    """
    Ansible 的Task
    """
    name = models.CharField(max_length=128, verbose_name=_('Task name'))
    module_name = models.CharField(max_length=128, verbose_name=_('Task module'))
    module_args = models.CharField(max_length=512, blank=True, verbose_name=_("Module args"))

    def __unicode__(self):
        return "%s" % self.name


class Play(models.Model):
    """
    Playbook 模板, 定义好Template后生成 Playbook
    """

