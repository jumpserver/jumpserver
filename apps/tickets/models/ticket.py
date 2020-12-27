# -*- coding: utf-8 -*-
#
import textwrap
import json
import uuid
from datetime import datetime
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from common.mixins.models import CommonModelMixin
from orgs.mixins.models import OrgModelMixin
from orgs.utils import tmp_to_root_org
from .. import const
from .mixin import TicketModelMixin

__all__ = ['Ticket', 'Comment']


class ModelJSONFieldEncoder(json.JSONEncoder):
    """ 解决一些类型的字段不能序列化的问题 """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime(settings.DATETIME_DISPLAY_FORMAT)
        if isinstance(obj, uuid.UUID):
            return str(obj)
        else:
            return super().default(obj)


class Ticket(TicketModelMixin, CommonModelMixin, OrgModelMixin):
    title = models.CharField(max_length=256, verbose_name=_("Title"))
    type = models.CharField(
        max_length=64, choices=const.TicketTypeChoices.choices,
        default=const.TicketTypeChoices.general.value, verbose_name=_("Type")
    )
    meta = models.JSONField(encoder=ModelJSONFieldEncoder, verbose_name=_("Meta"))
    action = models.CharField(
        choices=const.TicketActionChoices.choices, max_length=16, blank=True,
        default=const.TicketActionChoices.apply.value, verbose_name=_("Action")
    )
    status = models.CharField(
        max_length=16, choices=const.TicketStatusChoices.choices,
        default=const.TicketStatusChoices.open.value, verbose_name=_("Status")
    )
    # 申请人
    applicant = models.ForeignKey(
        'users.User', related_name='applied_tickets', on_delete=models.SET_NULL, null=True,
        verbose_name=_("Applicant")
    )
    applicant_display = models.CharField(
        max_length=128, default='No', verbose_name=_("Applicant display")
    )
    # 处理人
    processor = models.ForeignKey(
        'users.User', related_name='processed_tickets', on_delete=models.SET_NULL, null=True,
        verbose_name=_("Processor")
    )
    processor_display = models.CharField(
        max_length=128, blank=True, null=True, default='No', verbose_name=_("Processor display")
    )
    # 受理人列表
    assignees = models.ManyToManyField(
        'users.User', related_name='assigned_tickets', verbose_name=_("Assignees")
    )
    assignees_display = models.CharField(
        max_length=128, blank=True, default='No', verbose_name=_("Assignees display")
    )
    # 其他
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    def __str__(self):
        return '{}({})'.format(self.title, self.applicant_display)

    #: new =================================================
    def has_assignee(self, assignee):
        return self.assignees.filter(id=assignee.id).exists()

    # status
    @property
    def status_closed(self):
        return self.status == const.TicketStatusChoices.closed.value
    
    @property
    def status_open(self):
        return self.status == const.TicketStatusChoices.open.value

    # action
    @property
    def is_approved(self):
        return self.action == const.TicketActionChoices.approve.value

    @property
    def is_rejected(self):
        return self.action == const.TicketActionChoices.reject.value

    @property
    def is_closed(self):
        return self.action == const.TicketActionChoices.close.value

    # tickets
    @classmethod
    def get_all_tickets(cls):
        with tmp_to_root_org():
            return Ticket.objects.all()

    @classmethod
    def get_user_related_tickets(cls, user):
        tickets = cls.get_all_tickets()
        queries = None
        if user.is_superuser:
            pass
        elif user.is_super_auditor:
            pass
        elif user.is_org_admin:
            admin_orgs_id = [
                str(org_id) for org_id in user.admin_orgs.values_list('id', flat=True)
            ]
            assigned_tickets_id = [
                str(ticket_id) for ticket_id in user.assigned_tickets.values_list('id', flat=True)
            ]
            queries = Q(applicant=user)
            queries |= Q(processor=user)
            queries |= Q(org_id__in=admin_orgs_id)
            queries |= Q(id__in=assigned_tickets_id)
        elif user.is_org_auditor:
            audit_orgs_id = [
                str(org_id) for org_id in user.audit_orgs.values_list('id', flat=True)
            ]
            queries = Q(org_id__in=audit_orgs_id)
        elif user.is_common_user:
            queries = Q(applicant=user)
        else:
            tickets = Ticket.objects.none()
        if queries:
            tickets = tickets.filter(queries)
        return tickets.distinct()

    #: old =================================================
    def create_status_comment(self, status, user):
        if status == self.STATUS.CLOSED:
            action = _("Close")
        else:
            action = _("Open")
        body = _('{} {} this ticket').format(self.user, action)
        self.comments.create(user=user, body=body)

    def perform_status(self, status, user, extra_comment=None):
        self.old_create_comment(
            self.STATUS.get(status),
            user,
            extra_comment
        )
        self.status = status
        self.assignee = user
        self.save()

    def old_create_comment(self, action_display, user, extra_comment=None):
        body = '{} {} {}'.format(user, action_display, _("this ticket"))
        if extra_comment is not None:
            body += extra_comment
        self.comments.create(body=body, user=user, user_display=str(user))

    def perform_action(self, action, user, extra_comment=None):
        self.old_create_comment(
            self.ACTION.get(action),
            user,
            extra_comment
        )
        self.action = action
        self.status = self.STATUS.CLOSED
        self.assignee = user
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
