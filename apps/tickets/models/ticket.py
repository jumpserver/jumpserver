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
from tickets.const import TicketTypeChoices, TicketActionChoices, TicketStatusChoices
from tickets.signals import post_change_ticket_action
from tickets.handler import get_ticket_handler

__all__ = ['Ticket', 'ModelJSONFieldEncoder']


class ModelJSONFieldEncoder(json.JSONEncoder):
    """ 解决一些类型的字段不能序列化的问题 """
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime(settings.DATETIME_DISPLAY_FORMAT)
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, type(_("ugettext_lazy"))):
            return str(obj)
        else:
            return super().default(obj)


class Ticket(CommonModelMixin, OrgModelMixin):
    title = models.CharField(max_length=256, verbose_name=_("Title"))
    type = models.CharField(
        max_length=64, choices=TicketTypeChoices.choices,
        default=TicketTypeChoices.general.value, verbose_name=_("Type")
    )
    meta = models.JSONField(encoder=ModelJSONFieldEncoder, default=dict, verbose_name=_("Meta"))
    action = models.CharField(
        choices=TicketActionChoices.choices, max_length=16,
        default=TicketActionChoices.open.value, verbose_name=_("Action")
    )
    status = models.CharField(
        max_length=16, choices=TicketStatusChoices.choices,
        default=TicketStatusChoices.open.value, verbose_name=_("Status")
    )
    # 申请人
    applicant = models.ForeignKey(
        'users.User', related_name='applied_tickets', on_delete=models.SET_NULL, null=True,
        verbose_name=_("Applicant")
    )
    applicant_display = models.CharField(
        max_length=256, default='', verbose_name=_("Applicant display")
    )
    # 处理人
    processor = models.ForeignKey(
        'users.User', related_name='processed_tickets', on_delete=models.SET_NULL, null=True,
        verbose_name=_("Processor")
    )
    processor_display = models.CharField(
        max_length=256, blank=True, null=True, default='', verbose_name=_("Processor display")
    )
    # 受理人列表
    assignees = models.ManyToManyField(
        'users.User', related_name='assigned_tickets', verbose_name=_("Assignees")
    )
    assignees_display = models.JSONField(
        encoder=ModelJSONFieldEncoder, default=list, verbose_name=_('Assignees display')
    )
    # 评论
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))

    class Meta:
        ordering = ('-date_created',)

    def __str__(self):
        return '{}({})'.format(self.title, self.applicant_display)

    # type
    @property
    def type_apply_asset(self):
        return self.type == TicketTypeChoices.apply_asset.value

    @property
    def type_apply_application(self):
        return self.type == TicketTypeChoices.apply_application.value

    @property
    def type_login_confirm(self):
        return self.type == TicketTypeChoices.login_confirm.value

    # status
    @property
    def status_closed(self):
        return self.status == TicketStatusChoices.closed.value
    
    @property
    def status_open(self):
        return self.status == TicketStatusChoices.open.value

    def set_status_closed(self):
        self.status = TicketStatusChoices.closed.value

    # action
    @property
    def action_open(self):
        return self.action == TicketActionChoices.open.value

    @property
    def action_approve(self):
        return self.action == TicketActionChoices.approve.value

    @property
    def action_reject(self):
        return self.action == TicketActionChoices.reject.value

    @property
    def action_close(self):
        return self.action == TicketActionChoices.close.value

    # action changed
    def open(self, applicant):
        self.applicant = applicant
        self._change_action(action=TicketActionChoices.open.value)

    def approve(self, processor):
        self.processor = processor
        self._change_action(action=TicketActionChoices.approve.value)

    def reject(self, processor):
        self.processor = processor
        self._change_action(action=TicketActionChoices.reject.value)

    def close(self, processor):
        self.processor = processor
        self._change_action(action=TicketActionChoices.close.value)

    def _change_action(self, action):
        self.action = action
        self.save()
        post_change_ticket_action.send(sender=self.__class__, ticket=self, action=action)

    # ticket
    def has_assignee(self, assignee):
        return self.assignees.filter(id=assignee.id).exists()

    @classmethod
    def get_user_related_tickets(cls, user):
        queries = Q(applicant=user) | Q(assignees=user)
        tickets = cls.all().filter(queries).distinct()
        return tickets

    @classmethod
    def all(cls):
        with tmp_to_root_org():
            return Ticket.objects.all()

    def save(self, *args, **kwargs):
        """ 确保保存的org_id的是自身的值 """
        with tmp_to_org(self.org_id):
            return super().save(*args, **kwargs)

    @property
    def handler(self):
        return get_ticket_handler(ticket=self)

    # body
    @property
    def body(self):
        _body = self.handler.get_body()
        return _body
