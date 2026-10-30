from django.utils.translation import gettext
from datetime import timedelta
from types import SimpleNamespace

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.const import AutomationTypes, SecretStrategy, SecretType, DEFAULT_PASSWORD_RULES
from accounts.models import AutomationExecution, ChangeSecretRecord
from assets.tasks.common import generate_automation_execution_data
from common.const import Status
from common.utils import get_logger
from orgs.utils import tmp_to_org, tmp_to_root_org
from tickets.models import Ticket
from tickets.workflow.approvers import available_users
from tickets.workflow.errors import WorkflowConfigurationError
from .serializer import RequestSerializer

logger = get_logger(__name__)


def validate_context(ticket, context):
    serializer = RequestSerializer(data={
        'asset': context['request']['asset'], 'accounts': context['request']['accounts'],
    }, context={'org_id': ticket.org_id, 'request': SimpleNamespace(user=ticket.applicant)})
    if not serializer.is_valid():
        raise WorkflowConfigurationError(str(serializer.errors))
    expected = {(a['id'], a['username'], a['secret_type']) for a in context['accounts']}
    actual = {(str(pk), username, secret_type) for pk, username, secret_type in
              serializer.get_accounts(context['request']['asset']).filter(pk__in=[a[0] for a in expected])
              .values_list('id', 'username', 'secret_type')}
    if not expected or actual != expected:
        raise WorkflowConfigurationError(gettext('The requested accounts changed. Submit a new request.'))
    if not ticket.applicant_id or not available_users(ticket.org_id).filter(pk=ticket.applicant_id).exists():
        raise WorkflowConfigurationError(gettext('The applicant is no longer eligible for this operation.'))


def create_execution(instance, ticket):
    validate_context(ticket, instance.context)
    if instance.events.filter(type='action.submitted').exists():
        return None
    data = generate_automation_execution_data(f'Ticket {ticket.serial_num}', AutomationTypes.change_secret, {
        'ticket_id': str(ticket.pk),
        'accounts': [a['id'] for a in instance.context['accounts']],
        'assets': [instance.context['request']['asset']],
        'secret_type': SecretType.PASSWORD, 'secret_strategy': SecretStrategy.random,
        'password_rules': dict(DEFAULT_PASSWORD_RULES), 'check_conn_after_change': True,
    })
    # The queued execution is owned by its worker, never by a task approving the ticket.
    data['snapshot'].pop('celery_task_id', None)
    data['snapshot'].pop('celery_worker_hostname', None)
    execution, created = AutomationExecution.objects.get_or_create(
        pk=ticket.pk, defaults={'org_id': instance.org_id, 'type': AutomationTypes.change_secret,
                                'snapshot': data['snapshot']},
    )
    if not created:
        if (str(execution.org_id) != str(instance.org_id) or execution.type != AutomationTypes.change_secret
                or execution.snapshot.get('ticket_id') != str(ticket.pk)):
            raise WorkflowConfigurationError(gettext('The password change execution conflicts with an existing task.'))
        return None
    transaction.on_commit(lambda: dispatch_execution(execution.pk), robust=True)
    return {'action': 'submit_change_secret', 'pending': True,
            'resources': [{'type': 'change_secret_execution', 'id': str(execution.pk),
                           'name': data['snapshot']['name']}]}


def pending_executions():
    tickets = Ticket.objects.filter(
        type='change_secret', state='approved', workflow_instance__state='approved',
        workflow_instance__context__change_secret_version=1,
    )
    return AutomationExecution.objects.filter(
        pk__in=tickets.values('pk'), type=AutomationTypes.change_secret,
        status=Status.pending, date_start__isnull=True,
    ).filter(Q(result__dispatch_after__isnull=True) | Q(result__dispatch_after__lte=timezone.now().isoformat()))


def dispatch_execution(execution_id):
    from tickets.tasks import execute_ticket_change_secret
    with tmp_to_root_org(), transaction.atomic():
        execution = pending_executions().select_for_update().filter(pk=execution_id).first()
        if not execution:
            return
        execution.result = {'dispatch_after': (timezone.now() + timedelta(minutes=5)).isoformat()}
        execution.save(update_fields=['result'])
    try:
        execute_ticket_change_secret.delay(str(execution_id))
    except Exception as exc:
        # The pending execution is durable; the periodic dispatcher retries publication.
        logger.error('Unable to queue password change for ticket %s (%s)', execution_id, type(exc).__name__)


def execute(execution_id, task_id, hostname):
    with tmp_to_root_org(), transaction.atomic():
        execution = AutomationExecution.objects.select_for_update().filter(
            pk=execution_id, type=AutomationTypes.change_secret, status=Status.pending, date_start__isnull=True,
        ).first()
        if not execution or execution.snapshot.get('ticket_id') != str(execution.pk):
            return
        execution.status = Status.running
        execution.date_start = timezone.now()
        execution.snapshot.update(celery_task_id=task_id, celery_worker_hostname=hostname)
        execution.save(update_fields=['status', 'date_start', 'snapshot'])
    with tmp_to_org(execution.org_id):
        try:
            ticket = Ticket.objects.select_related('applicant', 'workflow_instance').get(
                pk=execution_id, org_id=execution.org_id, type='change_secret', state='approved',
                workflow_instance__state='approved', workflow_instance__context__change_secret_version=1,
            )
            validate_context(ticket, ticket.workflow_instance.context)
            if (set(execution.snapshot['accounts']) != {a['id'] for a in ticket.workflow_instance.context['accounts']}
                    or execution.snapshot['assets'] != [ticket.workflow_instance.context['request']['asset']]):
                raise WorkflowConfigurationError(gettext('The execution no longer matches the approved resources.'))
            execution.start()
        except Exception as exc:
            # Never expose runner exceptions: they may contain credentials or remote output.
            logger.error('Password change execution failed for ticket %s (%s)', execution_id, type(exc).__name__)
            AutomationExecution.objects.filter(pk=execution.pk, status=Status.running).update(
                status=Status.error, date_finished=timezone.now(), result={'ticket_error': 'execution_failed'},
            )


def get_result(ticket, user):
    from django.conf import settings
    result = {'state': 'pending' if ticket.state == 'pending' else 'unapproved', 'actions': []}
    if ticket.state != 'approved':
        return result
    with tmp_to_org(ticket.org_id):
        execution = AutomationExecution.objects.filter(
            pk=ticket.pk, org_id=ticket.org_id, type=AutomationTypes.change_secret,
        ).only('id', 'status', 'date_start', 'date_finished').first()
        if not execution:
            return {**result, 'state': 'unavailable'}
        accounts = ticket.workflow_instance.context['accounts']
        states = {str(pk): state for pk, state in ChangeSecretRecord.objects.filter(
            execution=execution, account_id__in=[a['id'] for a in accounts],
        ).values_list('account_id', 'status')}
        counts = {state: 0 for state in ('success', 'failed', 'unverified', 'pending')}
        for account in accounts:
            state = states.get(account['id'], 'pending')
            counts[state if state in counts else 'failed'] += 1
        processing = execution.status in (Status.pending, Status.running)
        if processing:
            state = 'queued' if execution.status == Status.pending else 'running'
        elif counts['unverified']:
            state = 'unverified'
        else:
            state = 'success' if counts['success'] == len(accounts) else 'failed'
        result.update(state=state, processing=processing, counts={**counts, 'total': len(accounts)},
                      execution_id=str(execution.pk),
                      date_start=execution.date_start.isoformat() if execution.date_start else None,
                      date_finished=execution.date_finished.isoformat() if execution.date_finished else None)
        if (settings.XPACK_LICENSE_IS_VALID and user and user.is_valid
                and 'accounts.view_changesecretexecution' in user.get_all_permissions()):
            task_id = execution.snapshot.get('celery_task_id')
            if task_id:
                result['log_task_id'] = task_id
    return result
