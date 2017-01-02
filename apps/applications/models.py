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
    type = models.CharField(choices=TYPE_CHOICES, max_length=3, blank=True, verbose_name=_('Terminal type'))
    user = models.OneToOneField(User, related_name='terminal', verbose_name='Application user',
                                null=True, on_delete=models.CASCADE)
    url = models.CharField(max_length=100, blank=True, verbose_name=_('URL to login'))
    is_accepted = models.BooleanField(default=False, verbose_name='Is Accepted')
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

    def create_related_app_user(self):
        user, access_key = User.create_app_user(name=self.name, comment=self.comment)
        self.user = user
        self.save()
        return user, access_key

    def delete(self, using=None, keep_parents=False):
        if self.user:
            self.user.delete()
        return super(Terminal, self).delete(using=using, keep_parents=keep_parents)

    def __unicode__(self):
        active = 'Active' if self.user and self.user.is_active else 'Disabled'
        return '%s: %s' % (self.name, active)

    __str__ = __unicode__

    class Meta:
        ordering = ('is_accepted',)


class TerminalHeatbeat(models.Model):
    terminal = models.ForeignKey(Terminal, on_delete=models.CASCADE)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'terminal_heatbeat'
