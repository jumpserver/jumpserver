from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from users.models import User


class Terminal(models.Model):
    TYPE_CHOICES = (
        ('S', 'SSH Terminal'),
        ('WT', 'Web Terminal')
    )
    name = models.CharField(max_length=30, verbose_name=_('Name'))
    ip = models.GenericIPAddressField(verbose_name=_('From ip'))
    is_active = models.BooleanField(default=False, verbose_name=_('Is active'))
    is_bound_ip = models.BooleanField(default=False, verbose_name=_('Is bound ip'))
    heatbeat_interval = models.IntegerField(default=60, verbose_name=_('Heatbeat interval'))
    type = models.CharField(choices=TYPE_CHOICES, max_length=2, verbose_name=_('Terminal type'))
    ssh_host = models.CharField(max_length=100, verbose_name=_('SSH host'))
    ssh_port = models.IntegerField(verbose_name=_('SSH port'))
    mail_to = models.ManyToManyField(User, verbose_name=_('Mail to'))
    date_created = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(verbose_name=_('Comment'))

    class Meta:
        db_table = 'terminal'
        ordering = ['name']


class TerminalHeatbeat(models.Model):
    terminal = models.ForeignKey(Terminal, on_delete=models.CASCADE)
    date_timestamp = models.IntegerField()

    class Meta:
        db_table = 'terminal_heatbeat'
