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


def apply_rotation_result(client, source, account_id, account_revision):
    from .manager import CredentialClientManager, client_uses_credential
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
    manager = object.__new__(CredentialClientManager)
    manager.client, manager.application = client, client.application
    manager._confirm_status(state, credential, timezone.now())


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
    if recipient.get('status') == 'success':
        return {'accepted': False, 'status': 'success'}
    source = ApplicationAudit.objects.get(id=event_id, org_id=client.org_id)
    if event.event != ApplicationEvent.CREDENTIAL_UPDATED:
        raise ValidationError(_('This event does not request a credential application result.'))
    if status == 'success':
        credential = ApplicationCredential.objects.filter(id=source.credential_id).first()
        if credential and credential.mode == 'alternating_rotation':
            apply_rotation_result(client, source, recipient.get('account_id'), recipient.get('account_revision'))
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
           result=status, summary=error_code or event.event)
    return {'accepted': True, 'status': status}


@transaction.atomic
def snapshot_result_event(client, credential, account, revision):
    """Retain a durable per-instance target across disconnects and startup."""
    sources = ApplicationAudit.objects.filter(
        credential_id=credential.id, revision=revision,
        org_id=client.org_id,
    ).values('id')
    for event in CredentialRotationEvent.objects.filter(
        source_event_id__in=sources, event=ApplicationEvent.CREDENTIAL_UPDATED,
        org_id=client.org_id,
    ).order_by('-published_at'):
        if any(item['id'] == str(client.id) and item.get('account_id') == str(account.id)
               and item.get('account_revision') == account.version for item in event.recipients):
            return str(event.source_event_id)
    source = record(AuditEvent.CREDENTIAL_REPUBLISHED, credential=credential, account=account,
                    application=client.application, revision=revision)
    rotation = credential.rotation_records.select_for_update().filter(date_finished__isnull=True).first()
    sequence = 1
    if rotation:
        from django.db.models import Max
        sequence = (rotation.events.aggregate(value=Max('sequence'))['value'] or 0) + 1
    CredentialRotationEvent.objects.create(
        rotation=rotation, source_event_id=source.id, event=ApplicationEvent.CREDENTIAL_UPDATED,
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
