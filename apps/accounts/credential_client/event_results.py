"""Application results are tied to durable events, never to a secret fetch."""
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from accounts.const import ApplicationEvent, AuditEvent
from accounts.models import (
    ApplicationAudit, ApplicationCommand, ApplicationCredential,
    CredentialApplicationBinding, CredentialClientStatus, CredentialRotationEvent,
)
from .audit import record


def rotation_state(client, source, account_id, account_revision):
    from .manager import client_uses_credential
    credential = ApplicationCredential.objects.select_for_update(of=('self',)).select_related(
        'active_account',
    ).filter(id=source.credential_id, is_active=True, applications=client.application).first()
    if not credential or not credential.authorized_applications().filter(id=client.application_id).exists():
        raise PermissionDenied(_('The event policy is no longer authorized.'))
    if not client_uses_credential(client, credential):
        raise PermissionDenied(_('The event is outside the Agent delivery scope.'))
    if (credential.current_revision != source.revision
            or str(credential.active_account_id) != str(account_id)
            or account_revision is None or credential.active_account.version != account_revision):
        raise ValidationError(_('The event account version is superseded.'))
    binding = CredentialApplicationBinding.objects.get(credential=credential, application=client.application)
    state, _created = CredentialClientStatus.objects.get_or_create(binding=binding, client=client)
    return credential, state


def apply_rotation_result(client, source, account_id, account_revision, skipped=False):
    from .manager import CredentialClientManager
    credential, state = rotation_state(client, source, account_id, account_revision)
    manager = object.__new__(CredentialClientManager)
    manager.client, manager.application = client, client.application
    manager._confirm_status(state, credential, timezone.now(), skipped=skipped)


def record_rotation_failure(client, source, account_id, account_revision, error_code):
    from uuid import uuid4
    credential, state = rotation_state(client, source, account_id, account_revision)
    previous = state.application_failure or {}
    # An unreviewed failure survives retries and later successful/skipped reports.
    if (previous.get('review_required') and previous.get('revision') == source.revision
            and previous.get('account_id') == str(account_id)
            and previous.get('account_revision') == account_revision):
        return previous
    state.application_failure = {
        'id': str(uuid4()), 'event_id': str(source.id), 'revision': source.revision,
        'account_id': str(account_id), 'account_revision': account_revision,
        'error_code': error_code, 'failed_at': timezone.now().isoformat(),
        'review_required': True,
    }
    state.save(update_fields=['application_failure', 'date_updated'])
    if credential.status in (credential.Status.waiting_switch, credential.Status.ready_for_change):
        if credential.status == credential.Status.ready_for_change:
            credential.status = credential.Status.waiting_switch
            credential.save(update_fields=['status', 'date_updated'])
        rotation = credential.rotation_records.filter(status='running', date_finished__isnull=True).first()
        if rotation:
            traffic = rotation.participant_snapshot.get('source_traffic', {})
            for key in ('switch_confirmed_at', 'started_at'):
                traffic.pop(key, None)
            rotation.save(update_fields=['participant_snapshot', 'date_updated'])

    return state.application_failure


@transaction.atomic
def report(client, event_id, status='success', error_code=''):
    from .commands import _valid_client, report as report_command
    _valid_client(client)
    command = ApplicationCommand.objects.filter(
        source_event_id=event_id, application_id=client.application_id, org_id=client.org_id,
    ).first()
    if command:
        # Commands still require an execution claim; success now also applies the
        # rotation result, without a separate credential confirmation request.
        return report_command(client, command.id, status, error_code)
    event = CredentialRotationEvent.objects.select_for_update().filter(
        source_event_id=event_id, org_id=client.org_id,
    ).first()
    if not event:
        raise NotFound()
    recipient = next((item for item in event.recipients
                      if item['id'] == str(client.id)
                      and item['application']['id'] == str(client.application_id)), None)
    if recipient is None:
        raise NotFound()
    if recipient.get('status') == status:
        return {'accepted': False, 'status': recipient['status']}
    source = ApplicationAudit.objects.get(id=event_id, org_id=client.org_id)
    if event.event not in ApplicationEvent.credential_application_events():
        raise ValidationError(_('This event does not request a credential application result.'))
    credential = ApplicationCredential.objects.filter(id=source.credential_id).first()
    if status == 'failed' and credential and credential.mode == 'alternating_rotation':
        recipient['failure_review'] = record_rotation_failure(
            client, source, recipient.get('account_id'), recipient.get('account_revision'), error_code)
    if status in ('success', 'skip'):
        if credential and credential.mode == 'alternating_rotation':
            apply_rotation_result(client, source, recipient.get('account_id'), recipient.get('account_revision'),
                                  skipped=status == 'skip')
        else:
            account = client.application.get_accounts().filter(id=recipient.get('account_id')).first()
            if not account or account.version != recipient.get('account_revision'):
                raise ValidationError(_('The event account version is no longer authorized or current.'))
    now = timezone.now().isoformat()
    recipient.update(status=status, finished_at=now,
                     received_at=recipient.get('received_at') or now, publish_result='published',
                     error_code=error_code if status == 'failed' else '')
    event.save(update_fields=['recipients', 'date_updated'])
    record(AuditEvent.COMMAND_RESULT, client=client, operation_id=event_id,
           result='failed' if status == 'failed' else 'success',
           summary=error_code or f'{event.event}: {status}')
    return {'accepted': True, 'status': status}


@transaction.atomic
def snapshot_result_event(client, credential, account, revision):
    """Retain a durable per-instance target across disconnects and startup."""
    sources = ApplicationAudit.objects.filter(
        credential_id=credential.id if credential else None, revision=revision,
        org_id=client.org_id,
        application_relations__application_id=client.application_id,
    )
    if credential is None:
        sources = sources.filter(account_id=account.id)
    for event in CredentialRotationEvent.objects.filter(
        source_event_id__in=sources.values('id'), event__in=ApplicationEvent.credential_application_events(),
        org_id=client.org_id,
    ).order_by('-published_at'):
        if any(item['id'] == str(client.id) and item.get('account_id') == str(account.id)
               and item.get('account_revision') == account.version for item in event.recipients):
            return str(event.source_event_id)
    source = record(AuditEvent.CREDENTIAL_REPUBLISHED, credential=credential, account=account,
                    application=client.application, revision=revision,
                    credential_key=credential.key if credential else f'account:{account.id}')
    rotation = credential.rotation_records.select_for_update().filter(date_finished__isnull=True).first() if credential else None
    sequence = 1
    if rotation:
        from django.db.models import Max
        sequence = (rotation.events.aggregate(value=Max('sequence'))['value'] or 0) + 1
    CredentialRotationEvent.objects.create(
        rotation=rotation, source_event_id=source.id, event=ApplicationEvent.CREDENTIAL_REFRESH_REQUESTED,
        sequence=sequence, revision=revision, org_id=client.org_id,
        recipients=[{
            'id': str(client.id), 'instance_id': client.instance_id, 'type': client.type,
            'application': {'id': str(client.application_id), 'name': client.application.name},
            'supports_receipts': client.event_receipts_supported,
            'publish_result': 'published', 'received_at': None,
            'account_id': str(account.id), 'account_revision': account.version,
            'status': 'pending', 'finished_at': None, 'error_code': '',
        }],
    )
    return str(source.id)


@transaction.atomic
def record_account_progress(client, account_id, revision, stage):
    """Fetching or writing a file is progress, independently of business success."""
    if stage not in ('fetched_at', 'delivered_at'):
        raise ValueError('Unknown credential progress stage')
    sources = ApplicationAudit.objects.filter(
        account_id=account_id, revision=revision, credential_id__isnull=True,
        org_id=client.org_id, application_relations__application_id=client.application_id,
    ).values('id')
    for event in CredentialRotationEvent.objects.select_for_update().filter(
        source_event_id__in=sources, event__in=ApplicationEvent.credential_application_events(), org_id=client.org_id,
    ):
        changed = False
        for recipient in event.recipients:
            if (recipient['id'] == str(client.id) and recipient.get('account_id') == str(account_id)
                    and recipient.get('account_revision') == revision and not recipient.get(stage)):
                recipient[stage] = timezone.now().isoformat()
                changed = True
        if changed:
            event.save(update_fields=['recipients', 'date_updated'])
