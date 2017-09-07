# -*- coding: utf-8 -*-
#

from django.db import models

__all__ = ['TaskConfig']


class TaskConfig(models.Model):
    name = models.CharField(max_length=200, verbose_name='Task Name')


class DeployConfig(models.Model):
    id = models.OneToOneField(to=TaskConfig, to_field='id', on_delete='CASCADE')
