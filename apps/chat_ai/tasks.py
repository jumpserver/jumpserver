import asyncio
from datetime import timedelta
from html import escape

from celery import current_app, shared_task
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.const.crontab import CRONTAB_AT_AM_TWO
from common.utils import get_logger
from ops.celery.decorator import register_as_period_task
from orgs.utils import tmp_to_org, tmp_to_root_org

from .agents import AgentRunner
from .agents.context import RequestAuthContext
from .models import (
    AgentRun, ApiCallAudit, Approval, Conversation, Message, MessageFile,
    MessageImage,
)
from .permissions import CHAT_AI_USE_PERMISSION


logger = get_logger(__name__)


ACTIVE_RUN_STATUSES = (
    AgentRun.Status.QUEUED,
    AgentRun.Status.RUNNING,
    AgentRun.Status.AWAITING_APPROVAL,
)
ACTIVE_APPROVAL_STATUSES = (
    Approval.Status.PENDING,
    Approval.Status.PROCESSING,
)


@shared_task(
    verbose_name=_('Expire Chat AI approvals'),
    description=_('Mark pending Chat AI write approvals as expired.'),
)
@register_as_period_task(interval=300)
def expire_chat_ai_approvals():
    now = timezone.now()
    approvals = Approval.objects.filter(
        status__in=(Approval.Status.PENDING, Approval.Status.PROCESSING),
        expires_at__lte=now,
    )
    rows = list(approvals.values_list('id', 'status', 'agent_run_id'))
    pending_ids = [pk for pk, approval_status, _ in rows if approval_status == Approval.Status.PENDING]
    processing_ids = [pk for pk, approval_status, _ in rows if approval_status == Approval.Status.PROCESSING]
    Approval.objects.filter(id__in=pending_ids).update(status=Approval.Status.EXPIRED)
    Approval.objects.filter(id__in=processing_ids).update(
        status=Approval.Status.FAILED, error='APPROVAL_EXECUTION_UNKNOWN'
    )
    pending_run_ids = [
        run_id for _, approval_status, run_id in rows
        if run_id and approval_status == Approval.Status.PENDING
    ]
    processing_run_ids = [
        run_id for _, approval_status, run_id in rows
        if run_id and approval_status == Approval.Status.PROCESSING
    ]
    pending_message_ids = list(
        AgentRun.objects.filter(id__in=pending_run_ids).values_list('assistant_message_id', flat=True)
    )
    processing_message_ids = list(
        AgentRun.objects.filter(id__in=processing_run_ids).values_list('assistant_message_id', flat=True)
    )
    AgentRun.objects.filter(id__in=pending_run_ids, status=AgentRun.Status.AWAITING_APPROVAL).update(
        status=AgentRun.Status.FAILED, finished_at=now, error='APPROVAL_EXPIRED'
    )
    AgentRun.objects.filter(id__in=processing_run_ids, status=AgentRun.Status.AWAITING_APPROVAL).update(
        status=AgentRun.Status.FAILED, finished_at=now, error='APPROVAL_EXECUTION_UNKNOWN'
    )
    Message.objects.filter(
        id__in=[message_id for message_id in pending_message_ids if message_id],
        status=Message.Status.AWAITING_APPROVAL,
    ).update(status=Message.Status.FAILED, error='APPROVAL_EXPIRED')
    Message.objects.filter(
        id__in=[message_id for message_id in processing_message_ids if message_id],
        status=Message.Status.AWAITING_APPROVAL,
    ).update(status=Message.Status.FAILED, error='APPROVAL_EXECUTION_UNKNOWN')
    return len(rows)


@shared_task(
    verbose_name=_('Clean up stale Chat AI runs'),
    description=_('Fail abandoned Chat AI runs so conversations can accept new messages.'),
)
@register_as_period_task(interval=300)
def cleanup_stale_chat_ai_runs():
    now = timezone.now()
    running_timeout = max(60, getattr(settings, 'CHAT_AI_STALE_RUN_TIMEOUT', 600))
    queued_timeout = max(60, getattr(settings, 'CHAT_AI_QUEUED_RUN_TIMEOUT', 3600))
    running_cutoff = now - timedelta(seconds=running_timeout)
    queued_cutoff = now - timedelta(seconds=queued_timeout)
    with transaction.atomic():
        running_rows = list(
            AgentRun.objects.select_for_update().filter(
                status=AgentRun.Status.RUNNING,
                date_updated__lte=running_cutoff,
            ).values_list('id', 'assistant_message_id')
        )
        queued_rows = list(
            AgentRun.objects.select_for_update().filter(
                status=AgentRun.Status.QUEUED,
                date_updated__lte=queued_cutoff,
            ).values_list('id', 'assistant_message_id', 'task_id')
        )
        running_run_ids = [run_id for run_id, _ in running_rows]
        running_message_ids = [message_id for _, message_id in running_rows if message_id]
        queued_run_ids = [run_id for run_id, _, _ in queued_rows]
        queued_message_ids = [message_id for _, message_id, _ in queued_rows if message_id]
        AgentRun.objects.filter(
            id__in=running_run_ids,
            status=AgentRun.Status.RUNNING,
        ).update(
            status=AgentRun.Status.FAILED,
            finished_at=now,
            error='AGENT_RUN_STALE',
            date_updated=now,
        )
        Message.objects.filter(
            id__in=running_message_ids,
            status=Message.Status.STREAMING,
        ).update(status=Message.Status.FAILED, error='AGENT_RUN_STALE', date_updated=now)
        AgentRun.objects.filter(
            id__in=queued_run_ids,
            status=AgentRun.Status.QUEUED,
        ).update(
            status=AgentRun.Status.FAILED,
            finished_at=now,
            error='AGENT_RUN_QUEUE_TIMEOUT',
            date_updated=now,
        )
        Message.objects.filter(
            id__in=queued_message_ids,
            status=Message.Status.PENDING,
        ).update(status=Message.Status.FAILED, error='AGENT_RUN_QUEUE_TIMEOUT', date_updated=now)
    if running_run_ids:
        try:
            cache.set_many(
                {f'chat-ai:cancel:{run_id}': True for run_id in running_run_ids},
                timeout=running_timeout,
            )
        except Exception:
            pass
    _revoke_tasks(task_id for _, _, task_id in queued_rows)
    return len(running_run_ids) + len(queued_run_ids)


def _retention_cutoff(setting_name):
    try:
        keep_days = int(getattr(settings, setting_name))
    except (AttributeError, TypeError, ValueError):
        logger.warning('Invalid Chat AI retention setting: %s', setting_name)
        return None
    if keep_days <= 0:
        return None
    return timezone.now() - timedelta(days=keep_days)


def _delete_in_batches(queryset, batch_size=1000):
    deleted = 0
    while True:
        ids = list(
            queryset.order_by('pk').values_list('pk', flat=True)[:batch_size]
        )
        if not ids:
            return deleted
        queryset.model.objects.filter(pk__in=ids).delete()
        deleted += len(ids)


def _clear_result_cards_in_batches(queryset, batch_size=1000):
    cleared = 0
    while True:
        ids = list(
            queryset.order_by('pk').values_list('pk', flat=True)[:batch_size]
        )
        if not ids:
            return cleared
        Message.objects.filter(pk__in=ids).update(result_cards=[])
        cleared += len(ids)


@shared_task(
    verbose_name=_('Clean up expired Chat AI data'),
    description=_(
        'Delete expired Chat AI conversations, attachments, result cards, and audit data.'
    ),
)
@register_as_period_task(crontab=CRONTAB_AT_AM_TWO)
def clean_chat_ai_data_period():
    counts = {
        'images': 0,
        'files': 0,
        'result_cards': 0,
        'api_call_audits': 0,
        'approvals': 0,
        'agent_runs': 0,
        'conversations': 0,
    }
    with tmp_to_root_org():
        attachment_cutoff = _retention_cutoff('CHAT_AI_ATTACHMENT_KEEP_DAYS')
        if attachment_cutoff:
            counts['images'] = _delete_in_batches(
                MessageImage.objects.filter(date_created__lt=attachment_cutoff)
                .exclude(
                    message__conversation__agent_runs__status__in=ACTIVE_RUN_STATUSES
                )
                .distinct()
            )
            counts['files'] = _delete_in_batches(
                MessageFile.objects.filter(date_created__lt=attachment_cutoff)
                .exclude(
                    message__conversation__agent_runs__status__in=ACTIVE_RUN_STATUSES
                )
                .distinct()
            )

        result_card_cutoff = _retention_cutoff('CHAT_AI_RESULT_CARD_KEEP_DAYS')
        if result_card_cutoff:
            counts['result_cards'] = _clear_result_cards_in_batches(
                Message.objects.filter(date_created__lt=result_card_cutoff).exclude(
                    result_cards=[]
                ).exclude(
                    conversation__agent_runs__status__in=ACTIVE_RUN_STATUSES
                ).distinct()
            )

        audit_cutoff = _retention_cutoff('CHAT_AI_AUDIT_KEEP_DAYS')
        if audit_cutoff:
            counts['api_call_audits'] = _delete_in_batches(
                ApiCallAudit.objects.filter(date_created__lt=audit_cutoff)
                .exclude(agent_run__status__in=ACTIVE_RUN_STATUSES)
                .exclude(approval__status__in=ACTIVE_APPROVAL_STATUSES)
                .distinct()
            )
            counts['approvals'] = _delete_in_batches(
                Approval.objects.filter(date_updated__lt=audit_cutoff).exclude(
                    status__in=ACTIVE_APPROVAL_STATUSES
                )
            )
            counts['agent_runs'] = _delete_in_batches(
                AgentRun.objects.filter(date_updated__lt=audit_cutoff).exclude(
                    status__in=ACTIVE_RUN_STATUSES
                ).exclude(
                    approvals__status__in=ACTIVE_APPROVAL_STATUSES
                ).distinct()
            )

        conversation_cutoff = _retention_cutoff('CHAT_AI_CONVERSATION_KEEP_DAYS')
        if conversation_cutoff:
            counts['conversations'] = _delete_in_batches(
                Conversation.objects.filter(date_updated__lt=conversation_cutoff)
                .exclude(
                    agent_runs__status__in=ACTIVE_RUN_STATUSES
                )
                .exclude(
                    approvals__status__in=ACTIVE_APPROVAL_STATUSES
                )
                .distinct()
            )
    logger.info('Chat AI retention cleanup completed: %s', counts)
    return counts


def _revoke_tasks(task_ids):
    for task_id in {str(item) for item in task_ids if item}:
        try:
            current_app.control.revoke(task_id, terminate=False)
        except Exception:
            logger.warning('Chat AI Celery task could not be revoked: %s', task_id)


def _run_result(agent_run_id):
    run = AgentRun.objects.filter(pk=agent_run_id).values(
        'id', 'conversation_id', 'status', 'error'
    ).first()
    if not run:
        return {'agent_run_id': str(agent_run_id), 'status': 'not_found', 'error': ''}
    return {
        'agent_run_id': str(run['id']),
        'conversation_id': str(run['conversation_id']) if run['conversation_id'] else '',
        'status': run['status'],
        'error': run['error'],
    }


def _start_queued_run(agent_run_id, task_id):
    now = timezone.now()
    with transaction.atomic():
        run = AgentRun.objects.select_for_update().get(pk=agent_run_id)
        if run.status != AgentRun.Status.QUEUED:
            return False
        if not run.task_id or str(run.task_id) != str(task_id):
            return False
        run.status = AgentRun.Status.RUNNING
        run.started_at = now
        run.error = ''
        run.save(update_fields=('status', 'started_at', 'error', 'date_updated'))
        if run.assistant_message_id:
            Message.objects.filter(
                pk=run.assistant_message_id,
                status=Message.Status.PENDING,
            ).update(status=Message.Status.STREAMING, date_updated=now)
    return True


async def _consume_runner(runner):
    async for _ in runner.stream():
        pass


def _notify_run(run):
    from notifications.site_msg import SiteMessageUtil

    message = run.assistant_message
    status = run.status.replace('_', ' ')
    preview = escape((message.content or message.error or '')[:1000])
    SiteMessageUtil.send_msg(
        subject=f'Chat AI: {escape(run.conversation.title or "Background task")}',
        message=(
            f'<p>Background Chat AI task finished with status <strong>{escape(status)}</strong>.</p>'
            f'<p>{preview}</p>'
        ),
        user_ids=[run.user_id],
    )


def execute_chat_ai_run(agent_run_id, *, web_search=False, read_only=False, notify=False):
    run = AgentRun.objects.select_related(
        'conversation', 'assistant_message', 'user'
    ).get(pk=agent_run_id)
    if run.status != AgentRun.Status.RUNNING:
        return _run_result(agent_run_id)
    with tmp_to_org(run.org_id):
        if not run.user.has_perm(CHAT_AI_USE_PERMISSION):
            raise PermissionError('Chat AI permission was revoked before execution.')
        user_message = run.conversation.messages.filter(
            role=Message.Role.USER,
            date_created__lte=run.assistant_message.date_created,
        ).order_by('-date_created').first()
        if not user_message:
            raise ValueError('Background Chat AI run has no user message.')
        runner = AgentRunner(
            conversation=run.conversation,
            user=run.user,
            user_message=user_message,
            assistant_message=run.assistant_message,
            agent_run=run,
            auth_context=RequestAuthContext(
                user_id=str(run.user_id),
                org_id=str(run.org_id),
                language=getattr(run.user, 'language', '') or '',
            ),
            web_search_enabled=web_search,
            read_only=read_only,
        )
        asyncio.run(_consume_runner(runner))
        run.refresh_from_db()
        if notify:
            try:
                _notify_run(run)
            except Exception:
                logger.warning(
                    'Chat AI run completed but its notification could not be sent: %s',
                    run.id,
                )
        return {
            'agent_run_id': str(run.id),
            'conversation_id': str(run.conversation_id),
            'status': run.status,
            'error': run.error,
        }


def _mark_run_failed(agent_run_id, error):
    now = timezone.now()
    code = str(error or 'BACKGROUND_RUN_FAILED')[:1024]
    with transaction.atomic():
        run = AgentRun.objects.select_for_update().filter(pk=agent_run_id).first()
        if not run or run.status not in (
            AgentRun.Status.QUEUED,
            AgentRun.Status.RUNNING,
        ):
            return False
        run.status = AgentRun.Status.FAILED
        run.finished_at = now
        run.error = code
        run.save(update_fields=('status', 'finished_at', 'error', 'date_updated'))
        if run.assistant_message_id:
            Message.objects.filter(
                pk=run.assistant_message_id,
                status__in=(Message.Status.PENDING, Message.Status.STREAMING),
            ).update(
                status=Message.Status.FAILED,
                error=code,
                date_updated=now,
            )
    return True


@shared_task(
    bind=True,
    verbose_name=_('Run Chat AI in background'),
    description=_('Execute a queued Chat AI request without keeping an SSE connection open.'),
)
def run_chat_ai_agent(self, agent_run_id, web_search=False, read_only=False, notify=True):
    try:
        if not _start_queued_run(agent_run_id, self.request.id):
            return _run_result(agent_run_id)
        return execute_chat_ai_run(
            agent_run_id,
            web_search=web_search,
            read_only=read_only,
            notify=notify,
        )
    except Exception as exc:
        _mark_run_failed(agent_run_id, exc.__class__.__name__)
        raise
