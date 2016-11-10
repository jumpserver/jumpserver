from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from users.models import User


class Terminal(models.Model):
    TYPE_CHOICES = (
        ('S', 'SSH Terminal'),
        ('WT', 'Web Terminal')
    )
    name = models.CharField(max_length=30, unique=True, verbose_name=_('Name'))
    ip = models.GenericIPAddressField(verbose_name=_('From ip'))
    is_active = models.BooleanField(default=False, verbose_name=_('Is active'))
    is_bound_ip = models.BooleanField(default=False, verbose_name=_('Is bound ip'))
    type = models.CharField(choices=TYPE_CHOICES, max_length=2, verbose_name=_('Terminal type'))
    url = models.CharField(max_length=100, verbose_name=_('URL to login'))
    date_created = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True, verbose_name=_('Comment'))

    def is_valid(self):
        return self.is_active and self.is_accepted

    @property
    def is_superuser(self):
        return False

    @property
    def is_terminal(self):
        return True

    class Meta:
        db_table = 'terminal'
        ordering = ['is_active']


class HeatbeatFailedLog(models.Model):
    """Terminal heatbeat failed log"""
    terminal = models.ForeignKey(Terminal, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'heatbeat_failed_log'
