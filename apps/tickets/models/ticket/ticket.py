# -*- coding: utf-8 -*-
#
import json
import uuid
from datetime import datetime
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

from common.mixins.models import CommonModelMixin
from orgs.mixins.models import OrgModelMixin
from orgs.utils import tmp_to_root_org, tmp_to_org
from tickets import const
from .mixin import TicketModelMixin

__all__ = ['Ticket']


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
        choices=const.TicketActionChoices.choices, max_length=16,
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
        max_length=256, default='No', verbose_name=_("Applicant display")
    )
    # 处理人
    processor = models.ForeignKey(
        'users.User', related_name='processed_tickets', on_delete=models.SET_NULL, null=True,
        verbose_name=_("Processor")
    )
    processor_display = models.CharField(
        max_length=256, blank=True, null=True, default='No', verbose_name=_("Processor display")
    )
    # 受理人列表
    assignees = models.ManyToManyField(
        'users.User', related_name='assigned_tickets', verbose_name=_("Assignees")
    )
    assignees_display = models.TextField(
        blank=True, default='No', verbose_name=_("Assignees display")
    )
    # 评论
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    class Meta:
        ordering = ('-date_created',)

    def __str__(self):
        return '{}({})'.format(self.title, self.applicant_display)


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
    def is_applied(self):
        return self.action == const.TicketActionChoices.apply.value

    @property
    def is_approved(self):
        return self.action == const.TicketActionChoices.approve.value

    @property
    def is_rejected(self):
        return self.action == const.TicketActionChoices.reject.value

    @property
    def is_closed(self):
        return self.action == const.TicketActionChoices.close.value

    @property
    def is_processed(self):
        return self.is_approved or self.is_rejected or self.is_closed

    # perform action
    def close(self, processor):
        self.processor = processor
        self.action = const.TicketActionChoices.close.value
        self.save()

    # tickets
    @classmethod
    def all(cls):
        with tmp_to_root_org():
            return Ticket.objects.all()

    @classmethod
    def get_user_related_tickets(cls, user):
        queries = None
        tickets = cls.all()
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
            tickets = cls.objects.none()
        if queries:
            tickets = tickets.filter(queries)
        return tickets.distinct()

    def save(self, *args, **kwargs):
        with tmp_to_org(self.org_id):
            # 确保保存的org_id的是自身的值
            return super().save(*args, **kwargs)
