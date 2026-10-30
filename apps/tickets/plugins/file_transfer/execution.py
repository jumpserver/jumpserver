import logging
import time
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from orgs.utils import tmp_to_org, tmp_to_root_org
from tickets.models import Ticket, TicketTransferExecution, TicketTransferFile, WorkflowEvent
from tickets.workflow.approvers import user_snapshot
from .policy import expires_at, validate_context, path_module
from .transport import TransferError

logger = logging.getLogger(__name__)


def event(ticket, event_type, **data):
    WorkflowEvent.objects.create(instance=ticket.workflow_instance, type=event_type, actor=ticket.applicant,
                                 actor_snapshot=user_snapshot(ticket.applicant), data=data)


def pending():
    return TicketTransferExecution.objects.filter(state='queued').filter(
        Q(dispatch_after__isnull=True) | Q(dispatch_after__lte=timezone.now()))


def dispatch(ticket_id):
    from tickets.tasks import execute_ticket_file_transfer
    with tmp_to_root_org(), transaction.atomic():
        execution = pending().select_for_update().filter(pk=ticket_id).first()
        if not execution:
            return
        execution.dispatch_after = timezone.now() + timedelta(minutes=5)
        execution.save(update_fields=['dispatch_after'])
    try:
        execute_ticket_file_transfer.delay(str(ticket_id))
    except Exception as exc:
        logger.error('Unable to queue ticket transfer %s (%s)', ticket_id, type(exc).__name__)


def execute(ticket_id):
    from audits.models import FTPLog
    from . import transport
    from .storage import reserve_download
    with tmp_to_root_org(), transaction.atomic():
        execution = TicketTransferExecution.objects.select_for_update().filter(pk=ticket_id, state='queued').first()
        if not execution:
            return
        execution.state, execution.date_started = 'running', timezone.now()
        execution.save(update_fields=['state', 'date_started'])
    with tmp_to_org(execution.org_id):
        ticket = Ticket.objects.select_related('applicant', 'workflow_instance').get(pk=ticket_id)
        context = ticket.workflow_instance.context
        if context['transfer_protocol'] == 'winrm':
            from . import winrm as transport
        direction = context['request']['direction']
        started, last_check = time.monotonic(), 0

        def guard(recheck=False):
            nonlocal last_check
            if timezone.now() >= expires_at(ticket) or time.monotonic() - started > 900:
                raise TransferError('expired')
            if recheck or time.monotonic() - last_check > 5:
                ticket.refresh_from_db()
                validate_context(ticket, approved=True, remote_addr=execution.remote_addr)
                last_check = time.monotonic()

        try:
            asset, account = validate_context(ticket, approved=True, remote_addr=execution.remote_addr)
            event(ticket, 'transfer.started')
            with transport.connect(asset, account, context['transfer_port']) as sftp:
                root = transport.transfer_root(sftp, asset, account, ticket.applicant)
                for item in execution.files:
                    record = None
                    try:
                        guard(recheck=True)
                        item['state'] = 'running'
                        execution.save(update_fields=['files'])
                        if direction == 'upload':
                            record = TicketTransferFile.objects.get(
                                pk=item['id'], ticket=ticket, owner=ticket.applicant, org_id=ticket.org_id,
                                kind='upload', purged_at__isnull=True, expires_at__gt=timezone.now(),
                            )
                            frozen = next(f for f in context['transfer_files'] if f['id'] == item['id'])
                            if record.summary() != frozen:
                                raise TransferError('source_changed')
                            transport.upload(sftp, root, record, item['path'], guard)
                        else:
                            record = reserve_download(ticket, path_module(context['transfer_protocol']).basename(item['path']))
                            transport.download(sftp, root, item['path'], record, guard)
                        item.update(record.summary(), state='success')
                    except Exception as exc:
                        code = error_code(exc)
                        item.update(state='unverified' if code == 'commit_uncertain' else 'failed', error=code)
                        if record and direction == 'download':
                            record.path.unlink(missing_ok=True)
                            record.purged_at = timezone.now()
                            record.save(update_fields=['purged_at'])
                        logger.warning('Ticket transfer %s file failed (%s)', ticket_id, type(exc).__name__)
                    finally:
                        execution.save(update_fields=['files'])
                        FTPLog.objects.create(org_id=ticket.org_id, user=str(ticket.applicant),
                                              asset=str(asset), account=account.username, remote_addr=execution.remote_addr,
                                              operate=direction, filename=item['path'][:1024], session=str(ticket.pk),
                                              is_success=item['state'] == 'success')
        except Exception as exc:
            logger.error('Ticket transfer %s failed (%s)', ticket_id, type(exc).__name__)
            for item in execution.files:
                if item['state'] in ('pending', 'running'):
                    item.update(state='failed', error=error_code(exc))
        finally:
            execution.state = ('unverified' if any(f['state'] == 'unverified' for f in execution.files) else
                               'success' if all(f['state'] == 'success' for f in execution.files) else 'failed')
            execution.date_finished = timezone.now()
            execution.save(update_fields=['state', 'files', 'date_finished'])
            event(ticket, 'transfer.finished', state=execution.state,
                  success=sum(f['state'] == 'success' for f in execution.files), total=len(execution.files))


def error_code(exc):
    from rest_framework.exceptions import PermissionDenied, ValidationError
    if isinstance(exc, TransferError):
        return exc.code
    if isinstance(exc, PermissionDenied):
        return 'access_changed'
    if isinstance(exc, ValidationError):
        return 'size_limit'
    if isinstance(exc, FileNotFoundError):
        return 'file_missing'
    if isinstance(exc, PermissionError):
        return 'permission_denied'
    return 'transfer_failed'


def get_result(ticket, user):
    from .actions import can_review
    context = ticket.workflow_instance.context
    paths = path_module(context['transfer_protocol'])
    result = {'version': 2, 'direction': context['request']['direction'], 'state': 'pending', 'actions': [],
              'files': context['transfer_files'], 'protocols': [context['transfer_protocol']]}
    if result['direction'] == 'upload':
        result['files'] = [{**item, 'path': paths.join(context['request']['target_directory'], item['name'])}
                           for item in context['transfer_files']]
    else:
        result['files'] = [{'name': paths.basename(path), 'path': path} for path in context['request']['paths']]
    if result['direction'] == 'upload' and can_review(ticket, user):
        result['reviewable_files'] = [str(pk) for pk in TicketTransferFile.objects.filter(
            ticket=ticket, kind='upload', purged_at__isnull=True, expires_at__gt=timezone.now(),
        ).values_list('pk', flat=True)]
    if ticket.state == 'pending':
        return result
    if ticket.state != 'approved':
        return {**result, 'state': 'unavailable'}
    result.update(state='ready', expires_at=expires_at(ticket).isoformat())
    execution = TicketTransferExecution.objects.filter(pk=ticket.pk, org_id=ticket.org_id).first()
    if execution:
        result.update(state=execution.state, files=execution.files,
                      processing=execution.state in ('queued', 'running'),
                      date_finished=execution.date_finished.isoformat() if execution.date_finished else None)
    if timezone.now() >= expires_at(ticket):
        result['expired'] = True
        if not execution:
            result['state'] = 'expired'
    elif user and user.pk == ticket.applicant_id:
        # Full access and ACL checks run again at the action and worker boundaries.
        if not execution:
            result['actions'] = [{'type': 'execute_transfer'}]
        elif context['request']['direction'] == 'download':
            result['actions'] = [{'type': 'download_transfer_file', 'file_id': item['id']}
                                 for item in execution.files if item['state'] == 'success']
    return result


def maintain():
    with tmp_to_root_org():
        ids = list(pending().order_by('date_created').values_list('pk', flat=True)[:100])
        for pk in ids:
            dispatch(pk)
        # Started transfers are never replayed: an interrupted upload may already exist remotely.
        stale = TicketTransferExecution.objects.filter(state='running',
                                                       date_started__lt=timezone.now() - timedelta(minutes=17))
        for execution in stale[:100]:
            with transaction.atomic():
                execution = stale.select_for_update().filter(pk=execution.pk).first()
                if not execution:
                    continue
                for item in execution.files:
                    if item['state'] in ('pending', 'running'):
                        item.update(state='unverified', error='interrupted')
                execution.state, execution.date_finished = 'unverified', timezone.now()
                execution.save(update_fields=['state', 'files', 'date_finished'])
    return len(ids)


def cleanup():
    purged = 0
    with tmp_to_root_org():
        files = TicketTransferFile.objects.filter(purged_at__isnull=True).filter(
            Q(expires_at__lte=timezone.now()) | Q(ticket__state__in=['rejected', 'closed', 'cancelled', 'expired', 'error'])
        ).exclude(ticket__transfer_execution__state='running')
        remaining = files
        while ids := list(remaining.order_by('pk').values_list('pk', flat=True)[:100]):
            for pk in ids:
                try:
                    with transaction.atomic():
                        record = TicketTransferFile.objects.select_for_update().filter(
                            pk=pk, pk__in=files.values('pk'),
                        ).first()
                        if record:
                            record.path.unlink(missing_ok=True)
                            record.purged_at = timezone.now()
                            record.save(update_fields=['purged_at'])
                            purged += 1
                except OSError as exc:
                    logger.error('Unable to purge ticket transfer file %s (%s)', pk, type(exc).__name__)
            # Advance past failed or no-longer-eligible files; retry failures on the next hourly run.
            remaining = files.filter(pk__gt=ids[-1])
    return purged
