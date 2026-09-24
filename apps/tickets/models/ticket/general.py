# -*- coding: utf-8 -*-
#
from typing import Callable

from django.db import models, transaction
from django.db.models import Q
from django.db.models.fields import related
from django.db.utils import IntegrityError
from django.utils.translation import gettext_lazy as _

from common.db.encoder import ModelJSONFieldEncoder
from common.db.models import JMSBaseModel
from common.exceptions import JMSException
from common.utils import reverse, get_logger
from common.utils.lock import DistributedLock
from common.utils.timezone import as_current_tz
from orgs.models import Organization
from orgs.utils import tmp_to_org
from tickets.const import (
    TicketType, TicketStatus, TicketState, TicketOrigin,
    TicketLevel, StepState, StepStatus
)
from tickets.errors import AlreadyClosed, TicketStateChanged
from tickets.plugins import ticket_type_choices
from ..flow import TicketFlow

logger = get_logger(__file__)

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

    @property
    def processor_display(self):
        processor = self.ticket_assignees.exclude(state=StepState.pending).first()
        return processor.assignee_display if processor else ''

    class Meta:
        verbose_name = _("Ticket step")


class TicketAssigneeQuerySet(models.QuerySet):
    def bulk_create(self, objs, *args, **kwargs):
        objs = list(objs)
        for obj in objs:
            obj.set_assignee_snapshot()
        return super().bulk_create(objs, *args, **kwargs)


class TicketAssignee(JMSBaseModel):
    assignee = models.ForeignKey(
        'users.User', related_name='ticket_assignees',
        on_delete=models.SET_NULL, null=True, verbose_name='Assignee'
    )
    state = models.CharField(
        choices=TicketState.choices, max_length=64,
        default=TicketState.pending
    )
    step = models.ForeignKey(
        'tickets.TicketStep', related_name='ticket_assignees',
        on_delete=models.CASCADE
    )

    assignee_display = models.CharField(max_length=258, default='', blank=True, editable=False)

    objects = TicketAssigneeQuerySet.as_manager()

    def set_assignee_snapshot(self):
        if self._state.adding and self.assignee_id:
            self.assignee_display = str(self.assignee)

    def save(self, *args, **kwargs):
        self.set_assignee_snapshot()
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = _('Ticket assignee')

    def __str__(self):
        return f'{self.assignee_display}_{self.step}'


class StatusMixin:
    """Business facade; all new approvals are executed by WorkflowEngine."""
    State = TicketState
    Status = TicketStatus

    def is_state(self, state):
        return self.state == state

    def is_status(self, status):
        return self.status == status

    def open(self):
        from tickets.workflow.business import submit_ticket
        return submit_ticket(self)

    def open_by_system(self, assignees, workflow=None):
        from tickets.workflow.business import submit_system_ticket
        return submit_system_ticket(self, assignees, workflow)

    @property
    def approval_tasks(self):
        from tickets.models import ApprovalTask
        return ApprovalTask.objects.filter(node_instance__instance__ticket_id=self.pk)

    def pending_task(self, user, task_id=None):
        from tickets.workflow.errors import WorkflowConflict
        tasks = self.approval_tasks.filter(assignee=user, state='pending',
                                           node_instance__instance__state='running')
        if task_id:
            tasks = tasks.filter(pk=task_id)
        task = tasks.first()
        if not task:
            raise WorkflowConflict()
        return task

    def approve(self, processor, task_id=None, comment=''):
        from tickets.workflow.engine import WorkflowEngine
        return WorkflowEngine().approve(self.pending_task(processor, task_id), processor, comment)

    def reject(self, processor, task_id=None, comment=''):
        from tickets.workflow.engine import WorkflowEngine
        return WorkflowEngine().reject(self.pending_task(processor, task_id), processor, comment)

    def close(self, user=None):
        from tickets.workflow.engine import WorkflowEngine
        return WorkflowEngine().cancel(self.workflow_instance, user or self.applicant)

    @property
    def current_assignees(self):
        return [task.assignee for task in self.approval_tasks.filter(
            state='pending', node_instance__instance__state='running'
        ).select_related('assignee') if task.assignee_id]

    def has_current_assignee(self, user):
        return self.approval_tasks.filter(
            assignee=user, state='pending', node_instance__instance__state='running'
        ).exists() if user and user.is_authenticated else False

    def has_all_assignee(self, user):
        return self.approval_tasks.filter(assignee=user).exists() if user else False

    @property
    def processor(self):
        task = self.approval_tasks.filter(state__in=['approved', 'rejected']).order_by('-date_finished').first()
        return task.assignee if task else None

    @property
    def processor_display(self):
        task = self.approval_tasks.filter(state__in=['approved', 'rejected']).order_by('-date_finished').first()
        if task:
            return task.assignee_snapshot.get('name', '')
        step = self.ticket_steps.order_by('-level').first()
        return step.processor_display if step else ''

    @property
    def process_map(self):
        instance = getattr(self, 'workflow_instance', None)
        if not instance:
            return self.legacy_process_map
        result = []
        runs = instance.node_instances.filter(node__type='approval').select_related('node').prefetch_related('tasks')
        for level, run in enumerate(runs.order_by('date_created', 'id'), 1):
            tasks = list(run.tasks.all())
            votes = [t for t in tasks if t.state in ('approved', 'rejected')]
            result.append({
                'state': 'pending' if run.state == 'running' else run.state,
                'name': run.node.name, 'approval_level': level,
                'assignees': [str(t.assignee_id) if t.assignee_id else None for t in tasks],
                'assignees_display': [t.assignee_snapshot.get('name', '') for t in tasks],
                'processor': str(votes[-1].assignee_id) if votes else None,
                'processor_display': ', '.join(t.assignee_snapshot.get('name', '') for t in votes),
                'approval_date': str(run.date_finished or ''),
            })
        return result

    @property
    def legacy_process_map(self):
        process_map = []
        for step in self.ticket_steps.all():
            processor_id = ''
            assignee_ids = []
            processor_display = ''
            assignees_display = []
            state = step.state
            prefetched = getattr(step, '_prefetched_objects_cache', {})
            if 'ticket_assignees' in prefetched:
                ticket_assignees = step.ticket_assignees.all()
            else:
                ticket_assignees = step.ticket_assignees.select_related('assignee')

            for i in ticket_assignees:
                assignee_id = i.assignee_id
                assignee_display = i.assignee_display

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



class Ticket(StatusMixin, JMSBaseModel):
    title = models.CharField(max_length=256, verbose_name=_('Title'))
    type = models.CharField(
        max_length=64, choices=ticket_type_choices,
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
    origin = models.CharField(
        max_length=16, choices=TicketOrigin.choices,
        default=TicketOrigin.manual, verbose_name=_('Ticket origin'),
    )
    # 申请人
    applicant = models.ForeignKey(
        'users.User', related_name='applied_tickets', null=True,
        on_delete=models.SET_NULL, verbose_name=_("Applicant")
    )
    cc_users = models.ManyToManyField(
        'users.User', related_name='cc_tickets', blank=True,
        verbose_name=_('CC users')
    )
    flow = models.ForeignKey(
        'TicketFlow', related_name='tickets', null=True,
        on_delete=models.SET_NULL, verbose_name=_('TicketFlow')
    )
    workflow = models.ForeignKey(
        'Workflow', related_name='tickets', null=True, blank=True,
        on_delete=models.PROTECT, verbose_name=_('Workflow'),
    )
    approval_step = models.SmallIntegerField(
        default=TicketLevel.one, choices=TicketLevel.choices, verbose_name=_('Approval step')
    )
    comment = models.TextField(default='', blank=True, verbose_name=_('Comment'))
    rel_snapshot = models.JSONField(verbose_name=_('Relation snapshot'), default=dict)
    serial_num = models.CharField(_('Serial number'), max_length=128, null=True)
    meta = models.JSONField(encoder=ModelJSONFieldEncoder, default=dict, verbose_name=_("Meta"))
    request_data = models.JSONField(default=dict, blank=True, verbose_name=_('Request parameters'))
    org_id = models.CharField(
        max_length=36, blank=True, default='', verbose_name=_('Organization'), db_index=True
    )

    TICKET_TYPE = TicketType.general

    class Meta:
        ordering = ('-date_created',)
        verbose_name = _('Ticket')
        unique_together = (
            ('serial_num',),
        )

    def __str__(self):
        return '{}({})'.format(self.title, self.applicant)

    def save(self, *args, **kwargs):
        if self.TICKET_TYPE != TicketType.general:
            self.type = self.TICKET_TYPE
        super().save(*args, **kwargs)

    @property
    def name(self):
        return self.title

    @name.setter
    def name(self, value):
        self.title = value

    # TODO 先单独处理一下
    @property
    def org_name(self):
        org = Organization.get_instance(self.org_id)
        return org.name

    def is_type(self, tp: TicketType):
        return self.type == tp

    @classmethod
    def get_user_related_tickets(cls, user):
        queries = (
            Q(applicant=user) |
            Q(ticket_steps__ticket_assignees__assignee=user) |
            Q(workflow_instance__node_instances__tasks__assignee=user) |
            Q(cc_users=user)
        )
        return cls.objects.filter(queries).distinct()

    def get_current_ticket_flow_approve(self):
        return self.flow.rules.filter(level=self.approval_step).first()

    @classmethod
    def all(cls):
        return cls.objects.all()

    def set_rel_snapshot(self, save=True):
        from tickets.models import WorkflowInstance
        if WorkflowInstance._base_manager.filter(ticket_id=self.pk).exists():
            return
        rel_fields = set()
        m2m_fields = set()
        excludes = ['ticket_ptr_id', 'ticket_ptr', 'flow_id', 'flow', 'workflow', 'workflow_id', 'applicant_id']
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

        ticket = Ticket.objects.filter(
            serial_num__startswith=date_prefix
        ).order_by('-serial_num').first()

        last_num = 0
        if ticket:
            last_num = ticket.serial_num[8:]
            last_num = int(last_num)
                
        next_num = last_num + 1
        if next_num > 9999:
            raise JMSException(
                detail=_("Today's ticket creation limit (9999) has been reached. Please try again tomorrow."),
                code="ticket_daily_limit_reached"
            )
        
        num = '%04d' % next_num
        return f'{date_prefix}{num}'

    def set_serial_num(self):
        if self.serial_num:
            return

        lock_key = 'TICKET_LOCK_SET_SERIAL_NUM'
        with DistributedLock(lock_key):
            try:
                self.serial_num = self.get_next_serial_num()
                self.save(update_fields=('serial_num',))
            except IntegrityError as e:
                logger.error(f'Set ticket serial number error: {e}')
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
        elif name == 'org_id':
            org = Organization.get_instance(value)
            value = org.name if org else ''
        elif isinstance(value, list):
            value = ', '.join(value)
        return value

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
        return {
            'check_ticket_api': check_ticket_api,
            'close_ticket_api': close_ticket_api,
            'ticket_detail_page_url': '{url}?type={type}'.format(
                url=url_ticket_detail_external, type=self.type
            ),
            'assignees': [str(user) for user in self.current_assignees]
        }


class SuperTicket(Ticket):
    class Meta:
        proxy = True
        verbose_name = _("Super ticket")


class SubTicketManager(models.Manager):
    pass
