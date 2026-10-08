"""Publish committed PAM events to clients and external notification rules."""
from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.const import ApplicationEvent, AuditEvent
from accounts.models import (
    ApplicationCredential, ApplicationEventDelivery, ApplicationWebhook,
    CredentialClientInstance, CredentialRotationEvent,
    CredentialRotationRecord, IntegrationApplication,
)
from accounts.webhooks import (
    WebhookValidationError, build_webhook_context, render_webhook_template,
)
from common.utils import get_logger
from .audit import record


logger = get_logger(__name__)

TRACKED_NON_ROTATION_EVENTS = {
    ApplicationEvent.CREDENTIAL_CHANGE_STARTED,
    ApplicationEvent.CREDENTIAL_CHANGE_COMPLETED,
    ApplicationEvent.CREDENTIAL_CHANGE_FAILED,
    ApplicationEvent.CREDENTIAL_UPDATED,
    ApplicationEvent.CREDENTIAL_REVOKED,
    ApplicationEvent.CONFIGURATION_UPDATED,
}


def application_group(application_id):
    return f'credential-app-{application_id}'


def enqueue(event, code, rotation=None):
    """Publish one domain event; delivery never participates in the source transaction."""
    try:
        with transaction.atomic():
            if rotation is not None:
                _track_rotation(event, code, rotation)
            else:
                _track_non_rotation(event, code)
    except Exception as exc:
        logger.warning('Cannot record credential event %s (%s).', event.id, type(exc).__name__)
    transaction.on_commit(lambda: _publish_stream(event.id, code))
    _enqueue_webhooks(event, code)


def _application_ids(event):
    ids = list(event.application_relations.values_list('application_id', flat=True))
    if event.service_id and event.service_id not in ids:
        ids.append(event.service_id)
    return ids


def _clients(event, code):
    clients = CredentialClientInstance.objects.filter(
        application_id__in=_application_ids(event), application__is_active=True,
        is_active=True, org_id=event.org_id,
    )
    if event.credential_id and code != 'credential.revoked':
        clients = clients.filter(
            application__credential_bindings__credential_id=event.credential_id,
        )
    return clients.distinct()


def event_account_version(event):
    from accounts.models import Account
    return Account.objects.filter(id=event.account_id).values_list('version', flat=True).first()


def _recipients(event, code):
    from accounts.models import Account
    credential = ApplicationCredential.objects.filter(id=event.credential_id).first()
    target_id = credential.active_account_id if credential and credential.mode == 'alternating_rotation' else event.account_id
    target_version = (event.revision if credential and credential.mode == 'subscription'
                      else Account.objects.filter(id=target_id).values_list('version', flat=True).first())
    clients = _clients(event, code).select_related('application').order_by('id')
    return [{
        'id': str(client.id), 'instance_id': client.instance_id, 'type': client.type,
        'application': {'id': str(client.application_id), 'name': client.application.name},
        'supports_receipts': client.event_receipts_supported,
        'publish_result': 'pending', 'received_at': None,
        'account_id': str(target_id) if target_id else None, 'account_revision': target_version,
        'status': 'pending', 'finished_at': None, 'error_code': '',
    } for client in clients]


def _track_rotation(event, code, rotation):
    # Serialize assignment before sending so equal timestamps retain publication order.
    rotation = CredentialRotationRecord.objects.select_for_update().get(
        id=rotation.id, credential_id=event.credential_id, org_id=event.org_id,
    )
    if rotation.events.filter(source_event_id=event.id).exists():
        return
    previous = rotation.events.order_by('-sequence').first()
    rotation.events.create(
        source_event_id=event.id, event=code, revision=event.revision,
        cycle_id=rotation.id,
        sequence=previous.sequence + 1 if previous else 1,
        recipients=_recipients(event, code), org_id=event.org_id,
    )


def _track_non_rotation(event, code):
    if code not in TRACKED_NON_ROTATION_EVENTS:
        return
    if (not event.credential_id and not _clients(event, code).exists()) or CredentialRotationEvent.objects.filter(
        source_event_id=event.id,
    ).exists():
        return
    CredentialRotationEvent.objects.create(
        rotation=None, source_event_id=event.id, event=code, sequence=1,
        cycle_id=event.operation_id or event.id,
        revision=event.revision, recipients=_recipients(event, code), org_id=event.org_id,
    )


def _publish_stream(event_id, code):
    try:
        _send_stream(event_id, code)
    except Exception:
        logger.warning('Cannot publish credential event %s.', event_id)


def _send_stream(event_id, code):
    from accounts.models import ApplicationAudit

    event = ApplicationAudit.objects.filter(id=event_id).first()
    if not event:
        return
    credential = ApplicationCredential.objects.filter(id=event.credential_id).first()
    credential_mode = credential.mode if credential else None
    application_ids = set(_clients(event, code).values_list('application_id', flat=True))
    try:
        tracked = CredentialRotationEvent.objects.filter(
            source_event_id=event_id, org_id=event.org_id,
        ).first()
    except Exception:
        tracked = None
        logger.warning('Cannot load rotation event recipients for %s.', event_id)
    payload = {
        'event_id': str(event.id),
        'event': code,
        'occurred_at': event.date_created.isoformat(),
        'credential_mode': credential_mode,
        'credential_key': event.credential_key or None,
        'revision': event.revision,
        'account_revision': (tracked.recipients[0].get('account_revision')
                             if tracked and tracked.recipients else event_account_version(event)),
        # Lifecycle audits may refer to the source account; the stream selector
        # always names the account currently published for an alternating policy.
        'account_id': (
            tracked.recipients[0].get('account_id') if tracked and tracked.recipients
            else str(credential.active_account_id) if credential and credential.account_switch
            else str(event.account_id) if event.account_id else None
        ),
        'operation_id': str(event.operation_id or event.rotation_id) if (event.operation_id or event.rotation_id) else None,
        'result': event.result,
    }
    if credential and credential.account_switch:
        payload['account_switch'] = credential.account_switch
    try:
        channel_layer = get_channel_layer()
    except Exception:
        channel_layer = None
    for application_id in application_ids:
        message = {'type': 'credential.event', 'payload': payload}
        if tracked is not None:
            # Match actual delivery to the same frozen identities that can ACK it.
            message['recipient_ids'] = [
                recipient['id'] for recipient in tracked.recipients
                if recipient['application']['id'] == str(application_id)
            ]
        result = 'published'
        try:
            if channel_layer is None:
                raise RuntimeError('Credential event channel is unavailable')
            async_to_sync(channel_layer.group_send)(
                application_group(application_id),
                message,
            )
        except Exception:
            result = 'failed'
            logger.warning('Cannot publish credential event %s to %s.', event_id, application_id)
        try:
            with transaction.atomic():
                publication = CredentialRotationEvent.objects.select_for_update().filter(
                    source_event_id=event_id, org_id=event.org_id,
                ).first()
                if publication:
                    for recipient in publication.recipients:
                        if recipient['application']['id'] == str(application_id):
                            if not recipient['received_at']:
                                recipient['publish_result'] = result
                    publication.save(update_fields=['recipients', 'date_updated'])
        except Exception:
            logger.warning('Cannot record credential event publication %s.', event_id)


def _enqueue_webhooks(event, code):
    application_ids = _application_ids(event)
    webhooks = ApplicationWebhook.objects.filter(
        applications__id__in=application_ids,
        org_id=event.org_id,
        applications__is_active=True,
        is_active=True,
    ).prefetch_related('applications').distinct()
    credential = ApplicationCredential.objects.filter(id=event.credential_id).first()
    applications = {
        application.id: application
        for application in IntegrationApplication.objects.filter(id__in=application_ids)
    }
    for webhook in webhooks:
        if code not in webhook.events:
            continue
        application = next((
            applications[item.id] for item in webhook.applications.all()
            if item.id in applications
        ), None)
        if not application:
            continue
        try:
            context = build_webhook_context(event, application, code)
            body = render_webhook_template(webhook.body_template, context)
        except WebhookValidationError:
            logger.warning('Skipping invalid application webhook %s.', webhook.id)
            continue
        try:
            with transaction.atomic():
                audit = record(
                    AuditEvent.NOTIFICATION, application=application,
                    credential=credential, result='pending',
                    summary='Waiting for webhook delivery.',
                )
                delivery = ApplicationEventDelivery.objects.create(
                    event=event, audit=audit, webhook=webhook, code=code,
                    url=webhook.url, method=webhook.method, headers=webhook.headers,
                    body=body, org_id=event.org_id,
                    expires_at=timezone.now() + timedelta(seconds=90),
                )
        except IntegrityError:
            continue
        transaction.on_commit(
            lambda delivery_id=delivery.id, org_id=delivery.org_id:
            _dispatch_webhook(delivery_id, str(org_id))
        )


def _dispatch_webhook(delivery_id, org_id):
    from accounts.tasks.application_events import dispatch_application_webhook

    dispatch_application_webhook(delivery_id, org_id)
