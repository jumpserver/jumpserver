from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from users.models import User


class Terminal(models.Model):
    TYPE_CHOICES = (
        ('SSH', 'SSH Terminal'),
        ('Web', 'Web Terminal')
    )
    name = models.CharField(max_length=30, unique=True, verbose_name=_('Name'))
    remote_addr = models.GenericIPAddressField(verbose_name=_('Remote address'), blank=True, null=True)
    type = models.CharField(choices=TYPE_CHOICES, max_length=2, verbose_name=_('Terminal type'))
    user = models.OneToOneField(User, verbose_name='Application user', null=True)
    url = models.CharField(max_length=100, verbose_name=_('URL to login'))
    date_created = models.DateTimeField(auto_now_add=True)
    comment = models.TextField(blank=True, verbose_name=_('Comment'))

    @property
    def is_active(self):
        if self.user and self.user.is_active:
            return True
        return False

    @is_active.setter
    def is_active(self, active):
        if self.user:
            self.user.is_active = active
            self.user.save()

    @property
    def is_accepted(self):
        if self.user:
            return True
        else:
            return False

    @is_accepted.setter
    def is_accepted(self, accepted):
        if accepted:
            user = User.create_app_user(name=self.name, comment=self.comment)
            self.user = user
            self.save()

    @property
    def is_superuser(self):
        return False

    @property
    def is_terminal(self):
        return True

    def __unicode__(self):
        active = 'Active' if self.user and self.user.is_active else 'Disabled'
        return '%s: %s' % (self.name, active)

    __str__ = __unicode__

    class Meta:
        db_table = 'terminal'


class TerminalHeatbeat(models.Model):
    terminal = models.ForeignKey(Terminal, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'terminal_heatbeat'
