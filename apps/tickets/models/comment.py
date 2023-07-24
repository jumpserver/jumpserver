# -*- coding: utf-8 -*-
#
from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import JMSBaseModel

__all__ = ['Comment']


class Comment(JMSBaseModel):
    class Type(models.TextChoices):
        state = 'state', _('State')
        common = 'common', _('common')

    ticket = models.ForeignKey(
        'tickets.Ticket', on_delete=models.CASCADE, related_name='comments'
    )
    user = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, related_name='comments',
        verbose_name=_("User")
    )
    user_display = models.CharField(max_length=256, verbose_name=_("User display name"))
    body = models.TextField(verbose_name=_("Body"))
    type = models.CharField(
        max_length=16, choices=Type.choices, default=Type.common, verbose_name=_("Type")
    )
    state = models.CharField(max_length=16, null=True)

    class Meta:
        ordering = ('date_created',)
        verbose_name = _("Comment")

    def set_display_fields(self):
        self.user_display = str(self.user)

    def __str__(self):
        return str(self.ticket)
