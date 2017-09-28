# ~*~ coding: utf-8 ~*~
from django.db import models

from django.utils.translation import ugettext_lazy as _
from separatedvaluesfield.models import TextSeparatedValuesField
from assets.models import *


class Task(models.Model):
    name = models.CharField(max_length=200, verbose_name=_('Name'))
    desc = models.CharField(max_length=2000, null=True, blank=True, verbose_name=_('Description'))
    ansible_role = models.CharField(max_length=200, verbose_name=_('Ansible Role'))
    tags = TextSeparatedValuesField(verbose_name=_('Tags'))
    assets = models.ManyToManyField(Asset, verbose_name=_('Assets'), related_name='task')
    groups = models.ManyToManyField(AssetGroup, verbose_name=_('Asset Groups'), related_name='task')
    system_user = models.ForeignKey(SystemUser, null=True, verbose_name=_('System User'), related_name='task')
    admin_user = models.ForeignKey(AdminUser, null=True, verbose_name=_('Admin User'), related_name='task')

