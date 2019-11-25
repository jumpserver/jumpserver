# -*- coding: utf-8 -*-
#

from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from common.mixins.models import CommonModelMixin
from common.fields.model import JsonDictTextField

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
    ACTION_APPROVE = 'approve'
    ACTION_REJECT = 'reject'
    ACTION_CHOICES = (
        (ACTION_APPROVE, _('Approve')),
        (ACTION_REJECT, _('Reject')),
    )
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='%(class)s_requested', verbose_name=_("User"))
    user_display = models.CharField(max_length=128, verbose_name=_("User display name"))

    title = models.CharField(max_length=256, verbose_name=_("Title"))
    body = models.TextField(verbose_name=_("Body"))
    meta = JsonDictTextField(verbose_name=_("Meta"), default='{}')
    assignee = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='%(class)s_handled', verbose_name=_("Assignee"))
    assignee_display = models.CharField(max_length=128, blank=True, null=True, verbose_name=_("Assignee display name"))
    assignees = models.ManyToManyField('users.User', related_name='%(class)s_assigned', verbose_name=_("Assignees"))
    assignees_display = models.CharField(max_length=128, verbose_name=_("Assignees display name"), blank=True)
    type = models.CharField(max_length=16, choices=TYPE_CHOICES, default=TYPE_GENERAL, verbose_name=_("Type"))
    status = models.CharField(choices=STATUS_CHOICES, max_length=16, default='open')
    action = models.CharField(choices=ACTION_CHOICES, max_length=16, default='', blank=True)

    def __str__(self):
        return '{}: {}'.format(self.user_display, self.title)

    @property
    def body_as_html(self):
        return self.body.replace('\n', '<br/>')

    @property
    def status_display(self):
        return self.get_status_display()

    @property
    def type_display(self):
        return self.get_type_display()

    @property
    def action_display(self):
        return self.get_action_display()

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

    def create_action_comment(self, action, user):
        action_display = dict(self.ACTION_CHOICES).get(action)
        body = '{} {} {}'.format(user, action_display, _("this ticket"))
        self.comments.create(body=body, user=user, user_display=str(user))

    def perform_action(self, action, user):
        self.create_action_comment(action, user)
        self.action = action
        self.status = self.STATUS_CLOSED
        self.assignee = user
        self.assignees_display = str(user)
        self.save()

    def is_assignee(self, user):
        return self.assignees.filter(id=user.id).exists()

    def is_user(self, user):
        return self.user == user

    @classmethod
    def get_related_tickets(cls, user, queryset=None):
        if queryset is None:
            queryset = cls.objects.all()
        queryset = queryset.filter(
            Q(assignees=user) | Q(user=user)
        ).distinct()
        return queryset

    @classmethod
    def get_assigned_tickets(cls, user, queryset=None):
        if queryset is None:
            queryset = cls.objects.all()
        queryset = queryset.filter(assignees=user)
        return queryset

    @classmethod
    def get_my_tickets(cls, user, queryset=None):
        if queryset is None:
            queryset = cls.objects.all()
        queryset = queryset.filter(user=user)
        return queryset

    class Meta:
        ordering = ('-date_created',)


class Comment(CommonModelMixin):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, verbose_name=_("User"), related_name='comments')
    user_display = models.CharField(max_length=128, verbose_name=_("User display name"))
    body = models.TextField(verbose_name=_("Body"))

    class Meta:
        ordering = ('date_created', )
