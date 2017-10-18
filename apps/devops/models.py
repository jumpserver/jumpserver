# ~*~ coding: utf-8 ~*~
from django.db import models

from django.utils.translation import ugettext_lazy as _
from separatedvaluesfield.models import TextSeparatedValuesField
from assets.models import *


class AnsibleRole(models.Model):
    name = models.CharField(max_length=200, verbose_name=_('Name'))

    def __str__(self):
        return str(self.name)


class Task(models.Model):
    name = models.CharField(max_length=200, verbose_name=_('Name'))
    desc = models.TextField(null=True, blank=True, verbose_name=_('Description'))
    ansible_role = models.ForeignKey(AnsibleRole, verbose_name=_('Ansible Role'), related_name='task')
    tags = TextSeparatedValuesField(verbose_name=_('Tags'), null=True, blank=True)
    assets = models.ManyToManyField(Asset, verbose_name=_('Assets'), related_name='task', blank=True)
    groups = models.ManyToManyField(AssetGroup, verbose_name=_('Asset Groups'), related_name='task', blank=True)
    system_user = models.ForeignKey(SystemUser, null=True, blank=True, verbose_name=_('System User'),
                                    related_name='task')
