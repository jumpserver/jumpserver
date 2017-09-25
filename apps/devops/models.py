# ~*~ coding: utf-8 ~*~
from django.db import models

from django.utils.translation import ugettext_lazy as _
from jsonfield import JSONField
from assets.models import *


class Task(models.Model):
    name = models.CharField(max_length=200, verbose_name=_('Name'))
    desc = models.CharField(max_length=2000, null=True, blank=True, verbose_name=_('Description'))
    ansible_role = models.CharField(max_length=200, verbose_name=_('Ansible Role'))
    tags = JSONField(verbose_name=_('Tags'))
    assets = models.ManyToManyField(Asset, verbose_name=_('Assets'), related_name='task')
    groups = models.ManyToManyField(AssetGroup, verbose_name=_('Asset Groups'), related_name='task')
