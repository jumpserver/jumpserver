# -*- coding: utf-8 -*-
#

from django.db import models
from django.utils.translation import ugettext_lazy as _

from common.mixins.models import CommonModelMixin

__all__ = ['Ticket', 'Comment']


class Ticket(CommonModelMixin):
    STATUS_OPEN = 'open'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = (
        (STATUS_OPEN, _("Open")),
        (STATUS_CLOSED, _("Closed"))
    )
    TYPE_GENERAL = 'general'
    TYPE_LOGIN_CONFIRM = 'login_confirm'
    TYPE_CHOICES = (
        (TYPE_GENERAL, _("General")),
        (TYPE_LOGIN_CONFIRM, _("Login confirm"))
    )
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='%(class)s_requested', verbose_name=_("User"))
    user_display = models.CharField(max_length=128, verbose_name=_("User display name"))

    title = models.CharField(max_length=256, verbose_name=_("Title"))
    body = models.TextField(verbose_name=_("Body"))
    assignee = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='%(class)s_handled', verbose_name=_("Assignee"))
    assignee_display = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Assignee display name"))
    assignees = models.ManyToManyField('users.User', related_name='%(class)s_assigned', verbose_name=_("Assignees"))
    assignees_display = models.CharField(max_length=128, verbose_name=_("Assignees display name"), blank=True)
    type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=TYPE_GENERAL, verbose_name=_("Type"))
    status = models.CharField(choices=STATUS_CHOICES, max_length=16, default='open')

    def __str__(self):
        return '{}: {}'.format(self.user_display, self.title)

    @property
    def body_as_html(self):
        return self.body.replace('\n', '<br/>')

    @property
    def status_display(self):
        return self.get_status_display()

    def create_status_comment(self, status, user):
        if status == self.STATUS_CLOSED:
            action = _("Close")
        else:
            action = _("Open")
        body = _('{} {} this ticket').format(self.user, action)
        self.comments.create(user=user, body=body)

    def perform_status(self, status, user):
        if self.status == status:
            return
        self.status = status
        self.save()

    class Meta:
        ordering = ('-date_created',)


class Comment(CommonModelMixin):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, verbose_name=_("User"), related_name='comments')
    user_display = models.CharField(max_length=128, verbose_name=_("User display name"))
    body = models.TextField(verbose_name=_("Body"))

    class Meta:
        ordering = ('date_created', )
