# -*- coding: utf-8 -*-
#
from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.mixins.models import CommonModelMixin

__all__ = ['Comment']


class Comment(CommonModelMixin):
    ticket = models.ForeignKey(
        'tickets.Ticket', on_delete=models.CASCADE, related_name='comments'
    )
    user = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL, null=True, related_name='comments',
        verbose_name=_("User")
    )
    user_display = models.CharField(max_length=256, verbose_name=_("User display name"))
    body = models.TextField(verbose_name=_("Body"))

    class Meta:
        ordering = ('date_created', )

    def set_display_fields(self):
        self.user_display = str(self.user)
