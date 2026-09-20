"""Application Webhook enqueueing from committed domain events."""
from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.const import AuditEvent
from accounts.models import (
    ApplicationCredential, ApplicationEventDelivery, ApplicationWebhook,
)
from accounts.webhooks import (
    WebhookValidationError, build_webhook_context, render_webhook_template,
)
from common.utils import get_logger
from .audit import record


logger = get_logger(__name__)


def enqueue(event, code):
    """Create application Webhook deliveries; clients never consume these events."""
    application_ids = [event.service_id] if event.service_id else []
    if not application_ids and event.credential_id:
        application_ids = ApplicationCredential.objects.filter(
            id=event.credential_id,
        ).values_list('applications__id', flat=True)
    webhooks = ApplicationWebhook.objects.filter(
        application_id__in=application_ids,
        org_id=event.org_id,
        application__is_active=True,
        is_active=True,
    ).select_related('application')
    credential = ApplicationCredential.objects.filter(id=event.credential_id).first()
    for webhook in webhooks:
        if code not in webhook.events:
            continue
        try:
            context = build_webhook_context(event, webhook.application, code)
            body = render_webhook_template(webhook.body_template, context)
        except WebhookValidationError:
            logger.warning('Skipping invalid application webhook %s.', webhook.id)
            continue
        try:
            with transaction.atomic():
                audit = record(
                    AuditEvent.NOTIFICATION, application=webhook.application,
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
            _dispatch_webhook(delivery_id, org_id)
        )


def _dispatch_webhook(delivery_id, org_id):
    from accounts.tasks.application_events import dispatch_application_webhook
    dispatch_application_webhook(delivery_id, org_id)
