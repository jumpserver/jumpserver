# -*- coding: utf-8 -*-
#
from typing import Callable

from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save, pre_save
from django.utils.translation import ugettext_lazy as _
from django.db.utils import IntegrityError
from django.db.models.fields.related import RelatedField

from common.exceptions import JMSException
from common.utils.timezone import as_current_tz
from common.mixins.models import CommonModelMixin
from common.db.encoder import ModelJSONFieldEncoder
from tickets.const import (
    TicketType, TicketStatus, TicketState, TicketApprovalLevel,
    ProcessStatus, TicketAction,
)
from tickets.signals import post_change_ticket_action
from tickets.handler import get_ticket_handler
from tickets.errors import AlreadyClosed

__all__ = ['Ticket', 'TicketStep', 'TicketAssignee', 'SuperTicket']


class TicketStep(CommonModelMixin):
    ticket = models.ForeignKey(
        'Ticket', related_name='ticket_steps', on_delete=models.CASCADE, verbose_name='Ticket'
    )
    level = models.SmallIntegerField(
        default=TicketApprovalLevel.one, choices=TicketApprovalLevel.choices,
        verbose_name=_('Approve level')
    )
    state = models.CharField(choices=ProcessStatus.choices, max_length=64, default=ProcessStatus.notified)

    class Meta:
        verbose_name = _("Ticket step")


class TicketAssignee(CommonModelMixin):
    assignee = models.ForeignKey(
        'users.User', related_name='ticket_assignees', on_delete=models.CASCADE, verbose_name='Assignee'
    )
    state = models.CharField(choices=ProcessStatus.choices, max_length=64, default=ProcessStatus.notified)
    step = models.ForeignKey('tickets.TicketStep', related_name='ticket_assignees', on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Ticket assignee')

    def __str__(self):
        return '{0.assignee.name}({0.assignee.username})_{0.step}'.format(self)


class StatusMixin:
    state: str
    status: str
    applicant: models.ForeignKey
    current_node: models.Manager
    save: Callable

    def set_state_approve(self):
        self.state = TicketState.approved

    def set_state_reject(self):
        self.state = TicketState.rejected

    def set_state_closed(self):
        self.state = TicketState.closed

    def set_status_closed(self):
        self.status = TicketStatus.closed

    # status
    @property
    def status_open(self):
        return self.status == TicketStatus.open.value

    @property
    def status_closed(self):
        return self.status == TicketStatus.closed.value

    @property
    def state_open(self):
        return self.state == TicketState.open.value

    @property
    def state_approve(self):
        return self.state == TicketState.approved.value

    @property
    def state_reject(self):
        return self.state == TicketState.rejected.value

    @property
    def state_close(self):
        return self.state == TicketState.closed.value

    # action changed
    def open(self, applicant):
        self.applicant = applicant
        self._change_action(TicketAction.open)

    def approve(self, processor):
        self.update_current_step_state_and_assignee(processor, TicketState.approved)
        self._change_action(TicketAction.approve)

    def reject(self, processor):
        self.update_current_step_state_and_assignee(processor, TicketState.rejected)
        self._change_action(TicketAction.reject)

    def close(self, processor):
        self.update_current_step_state_and_assignee(processor, TicketState.closed)
        self._change_action(TicketAction.close)

    def update_current_step_state_and_assignee(self, processor, state):
        if self.status_closed:
            raise AlreadyClosed
        if state != TicketState.approved:
            self.state = state
        current_node = self.current_node
        current_node.update(state=state)
        current_node.first().ticket_assignees.filter(assignee=processor).update(state=state)

    def _change_action(self, action):
        self.save()
        post_change_ticket_action.send(sender=self.__class__, ticket=self, action=action)


class Ticket(CommonModelMixin, StatusMixin):
    title = models.CharField(max_length=256, verbose_name=_("Title"))
    type = models.CharField(
        max_length=64, choices=TicketType.choices,
        default=TicketType.general, verbose_name=_("Type")
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
    process_map = models.JSONField(encoder=ModelJSONFieldEncoder, default=list, verbose_name=_("Process"))
    # 评论
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))
    flow = models.ForeignKey(
        'TicketFlow', related_name='tickets', on_delete=models.SET_NULL, null=True,
        verbose_name=_("TicketFlow")
    )
    serial_num = models.CharField(max_length=128, unique=True, null=True, verbose_name=_('Serial number'))
    rel_snapshot = models.JSONField(verbose_name=_("Relation snapshot"), default=dict)
    org_id = models.CharField(max_length=36, blank=True, default='', verbose_name=_("Organization"), db_index=True)

    class Meta:
        ordering = ('-date_created',)
        verbose_name = _('Ticket')

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

    @property
    def current_node(self):
        return self.ticket_steps.filter(level=self.approval_step)

    @property
    def processor(self):
        processor = self.current_node.first().ticket_assignees \
            .exclude(state=ProcessStatus.notified).first()
        return processor.assignee if processor else None

    def ignore_applicant(self, assignees, applicant=None):
        applicant = applicant if applicant else self.applicant
        if len(assignees) != 1:
            assignees = set(assignees) - {applicant, }
        return list(assignees)

    def create_related_node(self, applicant=None):
        org_id = self.flow.org_id
        approval_rule = self.get_current_ticket_flow_approve()
        ticket_step = TicketStep.objects.create(ticket=self, level=self.approval_step)
        ticket_assignees = []
        assignees = approval_rule.get_assignees(org_id=org_id)
        assignees = self.ignore_applicant(assignees, applicant)
        for assignee in assignees:
            ticket_assignees.append(TicketAssignee(step=ticket_step, assignee=assignee))
        TicketAssignee.objects.bulk_create(ticket_assignees)

    def create_process_map(self, applicant=None):
        org_id = self.flow.org_id
        approval_rules = self.flow.rules.order_by('level')
        nodes = list()
        for node in approval_rules:
            assignees = node.get_assignees(org_id=org_id)
            assignees = self.ignore_applicant(assignees, applicant)
            assignee_ids = [assignee.id for assignee in assignees]
            assignees_display = [str(assignee) for assignee in assignees]
            nodes.append(
                {
                    'approval_level': node.level,
                    'state': ProcessStatus.notified,
                    'assignees': assignee_ids,
                    'assignees_display': assignees_display
                }
            )
        return nodes

    # TODO 兼容不存在流的工单
    def create_process_map_and_node(self, assignees, applicant):
        assignees = self.ignore_applicant(assignees, applicant)
        self.process_map = [{
            'approval_level': 1,
            'state': 'notified',
            'assignees': [assignee.id for assignee in assignees],
            'assignees_display': [str(assignee) for assignee in assignees]
        }, ]
        self.save()
        ticket_step = TicketStep.objects.create(ticket=self, level=1)
        ticket_assignees = []
        for assignee in assignees:
            ticket_assignees.append(TicketAssignee(step=ticket_step, assignee=assignee))
        TicketAssignee.objects.bulk_create(ticket_assignees)

    def has_current_assignee(self, assignee):
        return self.ticket_steps.filter(ticket_assignees__assignee=assignee, level=self.approval_step).exists()

    def has_all_assignee(self, assignee):
        return self.ticket_steps.filter(ticket_assignees__assignee=assignee).exists()

    @classmethod
    def get_user_related_tickets(cls, user):
        queries = Q(applicant=user) | Q(ticket_steps__ticket_assignees__assignee=user)
        tickets = cls.objects.all().filter(queries).distinct()
        return tickets

    def get_current_ticket_flow_approve(self):
        return self.flow.rules.filter(level=self.approval_step).first()

    @classmethod
    def all(cls):
        return cls.objects.all()
    #
    # def save(self, **kwargs):
    #     created = self.date_created is None
    #     pre_save.send(sender=Ticket, instance=self)
    #     super().save(**kwargs)
    #     post_save.send(sender=Ticket, instance=self, created=created)

    def set_rel_snapshot(self, save=True):
        rel_fields = [field.name for field in self._meta.fields
                      if isinstance(field, RelatedField)]
        m2m_fields = [field.name for field in self._meta.fields
                      if isinstance(field, models.ManyToManyField)]
        snapshot = {}
        for field in rel_fields:
            value = getattr(self, field)
            if not value:
                continue

            if field in m2m_fields:
                value = [str(v) for v in value.all()]
            else:
                value = str(value)
            snapshot[field] = value

        self.rel_snapshot = snapshot
        if save:
            self.save()

    @property
    def handler(self):
        return get_ticket_handler(ticket=self)

    # body
    @property
    def body(self):
        _body = self.handler.get_body()
        return _body

    def get_next_serial_num(self):
        date_created = as_current_tz(self.date_created)
        date_prefix = date_created.strftime('%Y%m%d')

        ticket = Ticket.objects.all().select_for_update().filter(
            serial_num__startswith=date_prefix
        ).order_by('-date_created').first()

        last_num = 0
        if ticket:
            last_num = ticket.serial_num[8:]
            last_num = int(last_num)
        num = '%04d' % (last_num + 1)
        # 202212010001
        return '{}{}'.format(date_prefix, num)

    def set_serial_num(self, save=True):
        if self.serial_num:
            return

        try:
            self.serial_num = self.get_next_serial_num()
            if save:
                self.save(update_fields=('serial_num',))
        except IntegrityError as e:
            if e.args[0] == 1062:
                # 虽然做了 `select_for_update` 但是每天的第一条工单仍可能造成冲突
                # 但概率小，这里只报错，用户重新提交即可
                raise JMSException(detail=_('Please try again'), code='please_try_again')
            raise e


class SuperTicket(Ticket):
    class Meta:
        proxy = True
        verbose_name = _("Super ticket")
