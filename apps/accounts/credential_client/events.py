"""Publish committed PAM events to clients and external notification rules."""
from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.const import ApplicationEvent, AuditEvent
from accounts.models import (
    ApplicationCredential, ApplicationEventDelivery, ApplicationWebhook,
    ClientAccessConfiguration, CredentialClientInstance, CredentialRotationEvent,
    CredentialRotationRecord, IntegrationApplication,
)
from accounts.webhooks import (
    WebhookValidationError, build_webhook_context, render_webhook_template,
)
from common.utils import get_logger
from .audit import record


logger = get_logger(__name__)

SUBSCRIPTION_EVENTS = {
    ApplicationEvent.CREDENTIAL_CHANGE_STARTED,
    ApplicationEvent.CREDENTIAL_CHANGE_COMPLETED,
    ApplicationEvent.CREDENTIAL_CHANGE_FAILED,
    ApplicationEvent.CREDENTIAL_UPDATED,
    ApplicationEvent.CREDENTIAL_REVOKED,
    ApplicationEvent.CONFIGURATION_UPDATED,
}


def configuration_group(configuration_id):
    return f'credential-config-{configuration_id}'


def enqueue(event, code, rotation=None):
    """Publish one domain event; delivery never participates in the source transaction."""
    try:
        with transaction.atomic():
            if rotation is not None:
                _track_rotation(event, code, rotation)
            else:
                _track_subscription(event, code)
    except Exception as exc:
        logger.warning('Cannot record credential event %s (%s).', event.id, type(exc).__name__)
    transaction.on_commit(lambda: _publish_stream(event.id, code))
    _enqueue_webhooks(event, code)


def _application_ids(event):
    ids = list(event.application_relations.values_list('application_id', flat=True))
    if event.service_id and event.service_id not in ids:
        ids.append(event.service_id)
    return ids


def _configurations(event, code):
    configurations = ClientAccessConfiguration.objects.filter(
        org_id=event.org_id, is_active=True, application__is_active=True,
    )
    if code == 'credential.revoked' and event.service_id and event.credential_id:
        configurations = configurations.filter(
            application_id=event.service_id, credentials=event.credential_id,
        )
    elif event.credential_id:
        configurations = configurations.filter(
            credentials=event.credential_id,
            application__credential_bindings__credential_id=event.credential_id,
            application_id__in=_application_ids(event),
        )
    elif event.configuration_id:
        configurations = configurations.filter(id=event.configuration_id)
    else:
        configurations = configurations.filter(application_id__in=_application_ids(event))
    return configurations.distinct()


def _recipients(event, code):
    clients = CredentialClientInstance.objects.filter(
        configuration__in=_configurations(event, code), is_active=True,
        org_id=event.org_id,
    ).select_related('application', 'configuration').order_by('id')
    return [{
        'id': str(client.id), 'instance_id': client.instance_id, 'type': client.type,
        'application': {'id': str(client.application_id), 'name': client.application.name},
        'configuration': {'id': str(client.configuration_id), 'name': client.configuration.name},
        'supports_receipts': client.event_receipts_supported,
        'publish_result': 'pending', 'received_at': None,
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
        sequence=previous.sequence + 1 if previous else 1,
        recipients=_recipients(event, code), org_id=event.org_id,
    )


def _track_subscription(event, code):
    if code not in SUBSCRIPTION_EVENTS:
        return
    if event.credential_id:
        subscribed = ApplicationCredential.objects.filter(
            id=event.credential_id, mode=ApplicationCredential.Mode.subscription,
        ).exists()
    else:
        subscribed = _configurations(event, code).filter(
            credentials__mode=ApplicationCredential.Mode.subscription,
        ).exists()
    if not subscribed or CredentialRotationEvent.objects.filter(
        source_event_id=event.id,
    ).exists():
        return
    CredentialRotationEvent.objects.create(
        rotation=None, source_event_id=event.id, event=code, sequence=1,
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
    credential_mode = ApplicationCredential.objects.filter(
        id=event.credential_id,
    ).values_list('mode', flat=True).first()
    configurations = _configurations(event, code)
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
        'account_id': str(event.account_id) if event.account_id else None,
        'operation_id': str(event.rotation_id) if event.rotation_id else None,
        'result': event.result,
    }
    try:
        channel_layer = get_channel_layer()
    except Exception:
        channel_layer = None
    for configuration_id in configurations.values_list('id', flat=True).distinct():
        message = {'type': 'credential.event', 'payload': payload}
        if tracked is not None:
            # Match actual delivery to the same frozen identities that can ACK it.
            message['recipient_ids'] = [
                recipient['id'] for recipient in tracked.recipients
                if recipient['configuration']['id'] == str(configuration_id)
            ]
        result = 'published'
        try:
            if channel_layer is None:
                raise RuntimeError('Credential event channel is unavailable')
            async_to_sync(channel_layer.group_send)(
                configuration_group(configuration_id),
                message,
            )
        except Exception:
            result = 'failed'
            logger.warning('Cannot publish credential event %s to %s.', event_id, configuration_id)
        try:
            with transaction.atomic():
                publication = CredentialRotationEvent.objects.select_for_update().filter(
                    source_event_id=event_id, org_id=event.org_id,
                ).first()
                if publication:
                    for recipient in publication.recipients:
                        if recipient['configuration']['id'] == str(configuration_id):
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
