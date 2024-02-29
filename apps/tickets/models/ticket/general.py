# -*- coding: utf-8 -*-
#
import json
from typing import Callable

from django.db import models
from django.db.models import Prefetch, Q
from django.db.models.fields import related
from django.db.utils import IntegrityError
from django.forms import model_to_dict
from django.utils.translation import gettext_lazy as _

from common.db.encoder import ModelJSONFieldEncoder
from common.db.models import JMSBaseModel
from common.exceptions import JMSException
from common.utils import reverse
from common.utils.timezone import as_current_tz
from orgs.models import Organization
from orgs.utils import tmp_to_org
from tickets.const import (
    TicketType, TicketStatus, TicketState,
    TicketLevel, StepState, StepStatus
)
from tickets.errors import AlreadyClosed
from tickets.handlers import get_ticket_handler
from ..flow import TicketFlow

__all__ = [
    'Ticket', 'TicketStep', 'TicketAssignee',
    'SuperTicket', 'SubTicketManager'
]


class TicketStep(JMSBaseModel):
    ticket = models.ForeignKey(
        'Ticket', related_name='ticket_steps',
        on_delete=models.CASCADE, verbose_name='Ticket'
    )
    level = models.SmallIntegerField(
        default=TicketLevel.one, choices=TicketLevel.choices,
        verbose_name=_('Approve level')
    )
    state = models.CharField(
        max_length=64, choices=StepState.choices,
        default=StepState.pending, verbose_name=_("State")
    )
    status = models.CharField(
        max_length=16, choices=StepStatus.choices,
        default=StepStatus.pending
    )

    def change_state(self, state, processor):
        if state != StepState.closed:
            assignees = self.ticket_assignees.filter(assignee=processor)
            if not assignees:
                raise PermissionError('Only assignees can do this')
            assignees.update(state=state)
        self.status = StepStatus.closed
        self.state = state
        self.save(update_fields=['state', 'status', 'date_updated'])

    def set_active(self):
        self.status = StepStatus.active
        self.save(update_fields=['status'])

    def next(self):
        kwargs = dict(ticket=self.ticket, level=self.level + 1, status=StepStatus.pending)
        return self.__class__.objects.filter(**kwargs).first()

    @property
    def processor(self):
        processor = self.ticket_assignees.exclude(state=StepState.pending).first()
        return processor.assignee if processor else None

    class Meta:
        verbose_name = _("Ticket step")


class TicketAssignee(JMSBaseModel):
    assignee = models.ForeignKey(
        'users.User', related_name='ticket_assignees',
        on_delete=models.CASCADE, verbose_name='Assignee'
    )
    state = models.CharField(
        choices=TicketState.choices, max_length=64,
        default=TicketState.pending
    )
    step = models.ForeignKey(
        'tickets.TicketStep', related_name='ticket_assignees',
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = _('Ticket assignee')

    def __str__(self):
        return '{0.assignee.name}({0.assignee.username})_{0.step}'.format(self)


class StatusMixin:
    State = TicketState
    Status = TicketStatus

    state: str
    status: str
    applicant_id: str
    applicant: models.ForeignKey
    current_step: TicketStep
    save: Callable
    create_process_steps_by_flow: Callable
    create_process_steps_by_assignees: Callable
    assignees: Callable
    set_serial_num: Callable
    set_rel_snapshot: Callable
    approval_step: int
    handler: None
    flow: TicketFlow
    ticket_steps: models.Manager

    def is_state(self, state: TicketState):
        return self.state == state

    def is_status(self, status: TicketStatus):
        return self.status == status

    def _open(self):
        self.set_serial_num()
        self.set_rel_snapshot()
        self._change_state_by_applicant(TicketState.pending)

    def open(self):
        self.create_process_steps_by_flow()
        self._open()

    def open_by_system(self, assignees):
        self.create_process_steps_by_assignees(assignees)
        self._open()

    def approve(self, processor):
        self.set_rel_snapshot()
        self._change_state(StepState.approved, processor)

    def reject(self, processor):
        self._change_state(StepState.rejected, processor)

    def reopen(self):
        self._change_state_by_applicant(TicketState.reopen)

    def close(self):
        self._change_state(TicketState.closed, self.applicant)

    def _change_state_by_applicant(self, state):
        if state == TicketState.closed:
            self.status = TicketStatus.closed
        elif state in [TicketState.reopen, TicketState.pending]:
            self.status = TicketStatus.open
        else:
            raise ValueError("Not supported state: {}".format(state))

        self.state = state
        self.save(update_fields=['state', 'status'])
        self.handler.on_change_state(state)

    def _change_state(self, state, processor):
        if self.is_status(self.Status.closed):
            raise AlreadyClosed
        current_step = self.current_step
        current_step.change_state(state, processor)
        self._finish_or_next(current_step, state)

    def _finish_or_next(self, current_step, state):
        next_step = current_step.next()

        # 提前结束，或者最后一步
        if state in [TicketState.rejected, TicketState.closed] or not next_step:
            self.state = state
            self.status = Ticket.Status.closed
            self.save(update_fields=['state', 'status'])
            self.handler.on_step_state_change(current_step, state)
        else:
            self.handler.on_step_state_change(current_step, state)
            next_step.set_active()
            self.approval_step += 1
            self.save(update_fields=['approval_step'])

    @property
    def process_map(self):
        process_map = []
        for step in self.ticket_steps.all():
            processor_id = ''
            assignee_ids = []
            processor_display = ''
            assignees_display = []
            state = step.state
            for i in step.ticket_assignees.all().prefetch_related('assignee'):
                assignee_id = i.assignee_id
                assignee_display = str(i.assignee)

                if state != StepState.pending and state == i.state:
                    processor_id = assignee_id
                    processor_display = assignee_display
                if state == StepState.closed:
                    processor_id = self.applicant_id
                    processor_display = str(self.applicant)

                assignee_ids.append(assignee_id)
                assignees_display.append(assignee_display)

            step_info = {
                'state': state,
                'assignees': assignee_ids,
                'processor': processor_id,
                'approval_level': step.level,
                'assignees_display': assignees_display,
                'approval_date': str(step.date_updated),
                'processor_display': processor_display
            }
            process_map.append(step_info)
        return process_map

    def exclude_applicant(self, assignees, applicant=None):
        applicant = applicant if applicant else self.applicant
        if len(assignees) != 1:
            assignees = set(assignees) - {applicant, }
        return list(assignees)

    def create_process_steps_by_flow(self):
        org_id = self.flow.org_id
        flow_rules = self.flow.rules.order_by('level')
        for rule in flow_rules:
            assignees = rule.get_assignees(org_id=org_id)
            assignees = self.exclude_applicant(assignees, self.applicant)
            step = TicketStep.objects.create(ticket=self, level=rule.level)
            step_assignees = [TicketAssignee(step=step, assignee=user) for user in assignees]
            TicketAssignee.objects.bulk_create(step_assignees)

    def create_process_steps_by_assignees(self, assignees):
        step = TicketStep.objects.create(ticket=self, level=1)
        assignees = self.exclude_applicant(assignees, self.applicant)
        ticket_assignees = [TicketAssignee(step=step, assignee=user) for user in assignees]
        TicketAssignee.objects.bulk_create(ticket_assignees)

    @property
    def current_step(self):
        return self.ticket_steps.filter(level=self.approval_step).first()

    @property
    def current_assignees(self):
        ticket_assignees = self.current_step.ticket_assignees.all()
        return [i.assignee for i in ticket_assignees]

    @property
    def processor(self):
        """ 返回最后一步的处理人 """
        return self.current_step.processor

    def has_current_assignee(self, assignee):
        return self.ticket_steps.filter(
            level=self.approval_step,
            ticket_assignees__assignee=assignee,
        ).exists()

    def has_all_assignee(self, assignee):
        return self.ticket_steps.filter(ticket_assignees__assignee=assignee).exists()

    @property
    def handler(self):
        return get_ticket_handler(ticket=self)


class Ticket(StatusMixin, JMSBaseModel):
    title = models.CharField(max_length=256, verbose_name=_('Title'))
    type = models.CharField(
        max_length=64, choices=TicketType.choices,
        default=TicketType.general, verbose_name=_('Type')
    )
    state = models.CharField(
        max_length=16, choices=TicketState.choices,
        default=TicketState.pending, verbose_name=_('State')
    )
    status = models.CharField(
        max_length=16, choices=TicketStatus.choices,
        default=TicketStatus.open, verbose_name=_('Status')
    )
    # 申请人
    applicant = models.ForeignKey(
        'users.User', related_name='applied_tickets', null=True,
        on_delete=models.SET_NULL, verbose_name=_("Applicant")
    )
    flow = models.ForeignKey(
        'TicketFlow', related_name='tickets', null=True,
        on_delete=models.SET_NULL, verbose_name=_('TicketFlow')
    )
    approval_step = models.SmallIntegerField(
        default=TicketLevel.one, choices=TicketLevel.choices, verbose_name=_('Approval step')
    )
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))
    rel_snapshot = models.JSONField(verbose_name=_('Relation snapshot'), default=dict)
    serial_num = models.CharField(_('Serial number'), max_length=128, null=True)
    meta = models.JSONField(encoder=ModelJSONFieldEncoder, default=dict, verbose_name=_("Meta"))
    org_id = models.CharField(
        max_length=36, blank=True, default='', verbose_name=_('Organization'), db_index=True
    )

    class Meta:
        ordering = ('-date_created',)
        verbose_name = _('Ticket')
        unique_together = (
            ('serial_num',),
        )

    def __str__(self):
        return '{}({})'.format(self.title, self.applicant)

    @property
    def spec_ticket(self):
        attr = self.type.replace('_', '') + 'ticket'
        return getattr(self, attr)

    # TODO 先单独处理一下
    @property
    def org_name(self):
        org = Organization.get_instance(self.org_id)
        return org.name

    def is_type(self, tp: TicketType):
        return self.type == tp

    @classmethod
    def get_user_related_tickets(cls, user):
        queries = Q(applicant=user) | Q(ticket_steps__ticket_assignees__assignee=user)
        # TODO: 与 StatusMixin.process_map 内连表查询有部分重叠 有优化空间 待验证排除是否不影响其它调用
        prefetch_ticket_assignee = Prefetch('ticket_steps__ticket_assignees',
                                            queryset=TicketAssignee.objects.select_related('assignee'), )
        tickets = cls.objects.prefetch_related(prefetch_ticket_assignee) \
            .select_related('applicant') \
            .filter(queries) \
            .distinct()
        return tickets

    def get_current_ticket_flow_approve(self):
        return self.flow.rules.filter(level=self.approval_step).first()

    @classmethod
    def all(cls):
        return cls.objects.all()

    def set_rel_snapshot(self, save=True):
        rel_fields = set()
        m2m_fields = set()
        excludes = ['ticket_ptr_id', 'ticket_ptr', 'flow_id', 'flow', 'applicant_id']
        for name, field in self._meta._forward_fields_map.items():
            if name in excludes:
                continue
            if isinstance(field, related.RelatedField):
                rel_fields.add(name)
            if isinstance(field, related.ManyToManyField):
                m2m_fields.add(name)

        snapshot = {}
        with tmp_to_org(self.org_id):
            for field in rel_fields:
                value = getattr(self, field)

                if field in m2m_fields:
                    value = [str(v) for v in value.all()]
                else:
                    value = str(value) if value else ''
                snapshot[field] = value

        self.rel_snapshot.update(snapshot)
        if save:
            self.save(update_fields=('rel_snapshot',))

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
        return '{}{}'.format(date_prefix, num)

    def set_serial_num(self):
        if self.serial_num:
            return

        try:
            self.serial_num = self.get_next_serial_num()
            self.save(update_fields=('serial_num',))
        except IntegrityError as e:
            if e.args[0] == 1062:
                # 虽然做了 `select_for_update` 但是每天的第一条工单仍可能造成冲突
                # 但概率小，这里只报错，用户重新提交即可
                raise JMSException(detail=_('Please try again'), code='please_try_again')
            raise e

    def get_field_display(self, name, field, data: dict):
        value = data.get(name)
        if hasattr(self, f'get_{name}_display'):
            value = getattr(self, f'get_{name}_display')()
        elif isinstance(field, related.ForeignKey):
            value = self.rel_snapshot[name]
        elif isinstance(field, related.ManyToManyField):
            if isinstance(self.rel_snapshot[name], str):
                value = self.rel_snapshot[name]
            elif isinstance(self.rel_snapshot[name], list):
                value = ','.join(self.rel_snapshot[name])
        elif isinstance(value, list):
            value = ', '.join(value)
        return value

    def get_local_snapshot(self):
        snapshot = {}
        excludes = ['ticket_ptr']
        fields = self._meta._forward_fields_map
        json_data = json.dumps(model_to_dict(self), cls=ModelJSONFieldEncoder)
        data = json.loads(json_data)
        local_fields = self._meta.local_fields + self._meta.local_many_to_many
        item_names = [field.name for field in local_fields if field.name not in excludes]
        for name in item_names:
            field = fields[name]
            value = self.get_field_display(name, field, data)
            snapshot[field.verbose_name] = value
        return snapshot

    def get_extra_info_of_review(self, user=None):
        if user and user.is_service_account:
            url_ticket_status = reverse(
                view_name='api-tickets:super-ticket-status', kwargs={'pk': str(self.id)}
            )
            check_ticket_api = {'method': 'GET', 'url': url_ticket_status}
            close_ticket_api = {'method': 'DELETE', 'url': url_ticket_status}
        else:
            url_ticket_status = reverse(
                view_name='api-tickets:ticket-detail', kwargs={'pk': str(self.id)}
            )
            url_ticket_close = reverse(
                view_name='api-tickets:ticket-close', kwargs={'pk': str(self.id)}
            )
            check_ticket_api = {'method': 'GET', 'url': url_ticket_status}
            close_ticket_api = {'method': 'PUT', 'url': url_ticket_close}

        url_ticket_detail_external = reverse(
            view_name='api-tickets:ticket-detail',
            kwargs={'pk': str(self.id)},
            external=True,
            api_to_ui=True
        )
        ticket_assignees = self.current_step.ticket_assignees.all()
        return {
            'check_ticket_api': check_ticket_api,
            'close_ticket_api': close_ticket_api,
            'ticket_detail_page_url': '{url}?type={type}'.format(
                url=url_ticket_detail_external, type=self.type
            ),
            'assignees': [str(ticket_assignee.assignee) for ticket_assignee in ticket_assignees]
        }


class SuperTicket(Ticket):
    class Meta:
        proxy = True
        verbose_name = _("Super ticket")


class SubTicketManager(models.Manager):
    pass
