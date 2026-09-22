"""Publish committed PAM events to clients and external notification rules."""
from datetime import timedelta

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.const import AuditEvent
from accounts.models import (
    ApplicationCredential, ApplicationEventDelivery, ApplicationWebhook,
    ClientAccessConfiguration, IntegrationApplication,
)
from accounts.webhooks import (
    WebhookValidationError, build_webhook_context, render_webhook_template,
)
from common.utils import get_logger
from .audit import record


logger = get_logger(__name__)


def configuration_group(configuration_id):
    return f'credential-config-{configuration_id}'


def enqueue(event, code):
    """Publish one domain event; delivery never participates in the source transaction."""
    transaction.on_commit(lambda: _publish_stream(event.id, code))
    _enqueue_webhooks(event, code)


def _application_ids(event):
    ids = list(event.application_relations.values_list('application_id', flat=True))
    if event.service_id and event.service_id not in ids:
        ids.append(event.service_id)
    return ids


def _publish_stream(event_id, code):
    from accounts.models import ApplicationAudit

    event = ApplicationAudit.objects.filter(id=event_id).first()
    if not event:
        return
    credential_mode = ApplicationCredential.objects.filter(
        id=event.credential_id,
    ).values_list('mode', flat=True).first()
    configurations = ClientAccessConfiguration.objects.filter(
        is_active=True, application__is_active=True,
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
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    for configuration_id in configurations.values_list('id', flat=True).distinct():
        async_to_sync(channel_layer.group_send)(
            configuration_group(configuration_id),
            {'type': 'credential.event', 'payload': payload},
        )


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
