# -*- coding: utf-8 -*-
#
from django.db import models
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _

from common.mixins.models import CommonModelMixin
from common.db.encoder import ModelJSONFieldEncoder
from orgs.mixins.models import OrgModelMixin
from orgs.utils import tmp_to_root_org, tmp_to_org
from tickets.const import TicketType, TicketStatus, TicketState, TicketApprovalLevel, ProcessStatus
from tickets.signals import post_change_ticket_action
from tickets.handler import get_ticket_handler

__all__ = ['Ticket']


class TicketStep(CommonModelMixin):
    ticket = models.ForeignKey(
        'Ticket', related_name='m2m_ticket_users', on_delete=models.CASCADE, verbose_name='Ticket'
    )
    level = models.SmallIntegerField(
        default=TicketApprovalLevel.one, choices=TicketApprovalLevel.choices,
        verbose_name=_('Approve level')
    )
    state = models.CharField(choices=ProcessStatus.choices, default=ProcessStatus.notified)


class TicketAssignee(CommonModelMixin):
    assignee = models.ForeignKey(
        'users.User', related_name='m2m_user_tickets', on_delete=models.CASCADE, verbose_name='User'
    )
    state = models.CharField(choices=ProcessStatus.choices, default=ProcessStatus.notified)
    step = models.ForeignKey('tickets.TicketStep', on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Ticket assignee')

    def __str__(self):
        return '{0.assignee.name}({0.assignee.username})_{0.step}'.format(self)


class Ticket(CommonModelMixin, OrgModelMixin):
    title = models.CharField(max_length=256, verbose_name=_("Title"))
    type = models.CharField(
        max_length=64, choices=TicketType.choices,
        default=TicketType.general.value, verbose_name=_("Type")
    )
    meta = models.JSONField(encoder=ModelJSONFieldEncoder, default=dict, verbose_name=_("Meta"))
    state = models.CharField(
        max_length=16, choices=TicketState.choices,
        default=TicketState.open, verbose_name=_("State")
    )
    status = models.CharField(
        max_length=16, choices=TicketStatus.choices,
        default=TicketStatus.open, verbose_name=_("Status")
    )
    approval_step = models.SmallIntegerField(
        default=TicketApprovalLevel.one, choices=TicketApprovalLevel.choices,
        verbose_name=_('Approval step')
    )
    # 申请人
    applicant = models.ForeignKey(
        'users.User', related_name='applied_tickets', on_delete=models.SET_NULL, null=True,
        verbose_name=_("Applicant")
    )
    applicant_display = models.CharField(max_length=256, default='', verbose_name=_("Applicant display"))
    # 受理人列表
    assignees = models.ManyToManyField(
        'users.User', related_name='assigned_tickets', verbose_name=_("Assignees"), through='TicketProcess'
    )
    process_map = models.JSONField(encoder=ModelJSONFieldEncoder, default=list, verbose_name=_("Process"))
    # 评论
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))
    flow = models.ForeignKey(
        'TicketFlow', related_name='tickets', on_delete=models.SET_NULL, null=True,
        verbose_name=_("TicketFlow")
    )

    class Meta:
        ordering = ('-date_created',)

    def __str__(self):
        return '{}({})'.format(self.title, self.applicant_display)

    # type
    @property
    def type_apply_asset(self):
        return self.type == TicketType.apply_asset.value

    @property
    def type_apply_application(self):
        return self.type == TicketType.apply_application.value

    @property
    def type_login_confirm(self):
        return self.type == TicketType.login_confirm.value

    # status
    @property
    def status_closed(self):
        return self.status == TicketStatus.closed.value

    @property
    def status_open(self):
        return self.status == TicketStatus.open.value

    def action_open(self, action=None):
        return action == TicketStatus.open.value

    @property
    def cur_assignees(self):
        return self.m2m_ticket_users.filter(approval_level=self.approval_level)

    @property
    def processor(self):
        level = self.approval_level
        m2m_ticket_users = self.m2m_ticket_users.filter(approval_level=level, is_processor=True).first()
        return m2m_ticket_users.user if m2m_ticket_users else None

    def set_action_approve(self):
        self.action = TicketStatus.approve.value

    def set_action_reject(self):
        self.action = TicketStatus.reject.value

    def set_action_closed(self):
        self.action = TicketStatus.close.value

    def set_status_closed(self):
        self.status = TicketStatus.closed.value

    def create_related_assignees(self):
        template_approve = self.get_ticket_flow_approve(self.approval_level)
        ticket_assignee_list = []
        assignees = template_approve.assignees.all()
        ticket_assignee_model = self.assignees.through
        for assignee in assignees:
            ticket_assignee_list.append(ticket_assignee_model(
                ticket=self, user=assignee, approval_level=self.approval_level))
        ticket_assignee_model.objects.bulk_create(ticket_assignee_list)
        return assignees

    def create_process_nodes(self):
        ticket_flow_approves = self.flow.ticket_flow_approves.order_by('approval_level')
        nodes = list()
        for node in ticket_flow_approves:
            assignees = node.assignees.all()
            nodes.append(
                {
                    'approval_level': node.approval_level,
                    'action': TicketStatus.open.value,
                    'assignees': [assignee.id for assignee in assignees],
                    'assignees_display': [str(assignee) for assignee in assignees]
                }
            )
        return nodes

    def change_action_and_processor(self, action, user):
        cur_assignees = self.cur_assignees
        cur_assignees.update(action=action)
        if action != TicketStatus.open.value:
            cur_assignees.filter(user=user).update(is_processor=True)
        else:
            self.applicant = user

    # action changed
    def open(self, applicant):
        action = TicketStatus.open.value
        self._change_action(action, applicant)

    def approve(self, processor):
        action = TicketStatus.approve.value
        self._change_action(action, processor)

    def reject(self, processor):
        action = TicketStatus.reject.value
        self._change_action(action, processor)

    def close(self, processor):
        action = TicketStatus.close.value
        self._change_action(action, processor)

    def _change_action(self, action, user):
        self.change_action_and_processor(action, user)
        self.save()
        post_change_ticket_action.send(sender=self.__class__, ticket=self, action=action)

    # ticket
    def has_assignee(self, assignee):
        return self.m2m_ticket_users.filter(user=assignee, approval_level=self.approval_level).exists()

    @classmethod
    def get_user_related_tickets(cls, user):
        queries = Q(applicant=user) | Q(assignees=user)
        tickets = cls.all().filter(queries).distinct()
        return tickets

    def get_ticket_flow_approve(self, level):
        return self.flow.ticket_flow_approves.filter(approval_level=level).first()

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



