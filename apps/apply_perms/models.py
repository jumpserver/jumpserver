from __future__ import unicode_literals, absolute_import
import functools

from django.db import models
from django.utils.translation import ugettext_lazy as _
from users.models import User

class ApplyPermission(models.Model):
    STATUS_CHOICES = (
        ('Applying', _('Applying')),
        ('Approved', _('Approved')),
        ('Disapproved', _('Disapproved')),
    )
    name = models.CharField(
        max_length=128, unique=True, verbose_name=_('Name'))
    user_groups = models.TextField(blank=True, verbose_name=_('User group'))
    assets = models.TextField(blank=True, verbose_name=_('Asset'))
    asset_groups = models.TextField(blank=True, verbose_name=_('Asset group'))
    system_users = models.TextField(blank=True, verbose_name=_('System user'))
    approver = models.ForeignKey(
        User, related_name="approval_tasks", verbose_name=_('Approver'))
    status = models.CharField(choices=STATUS_CHOICES, default='Applying', max_length=10, blank=True, verbose_name=_('Status'))
    date_applied = models.DateTimeField(auto_now=True, verbose_name=_('Date applied'))
    date_approved = models.DateTimeField(blank=True, null=True, verbose_name=_('Date approved'))

    def __unicode__(self):
        return self.name

    # def super_user(self):
    #     return User.objects.get(username='admin')

    class Meta:
        db_table = 'apply_permission'

