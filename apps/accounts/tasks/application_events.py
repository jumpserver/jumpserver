from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.const.crontab import CRONTAB_AT_AM_THREE
from common.utils import get_log_keep_day, get_logger
from ops.celery.decorator import register_as_period_task
from orgs.utils import tmp_to_org, tmp_to_root_org


logger = get_logger(__name__)
WEBHOOK_ATTEMPT_LIMIT = 3
WEBHOOK_RETRY_DELAYS = (5, 15)
WEBHOOK_CLAIM_LEASE = 25
APPLICATION_RECORD_CLEAN_BATCH_SIZE = 3000


def _delete_in_batches(queryset, batch_size=APPLICATION_RECORD_CLEAN_BATCH_SIZE):
    deleted = {}
    model = queryset.model
    while ids := list(queryset.order_by('date_created', 'id').values_list('id', flat=True)[:batch_size]):
        _, counts = model.objects.filter(id__in=ids).delete()
        for label, count in counts.items():
            deleted[label] = deleted.get(label, 0) + count
    return deleted


def dispatch_application_webhook(delivery_id, org_id, countdown=0):
    try:
        deliver_application_webhook.apply_async(
            args=(str(delivery_id), str(org_id)), countdown=countdown,
        )
    except Exception:
        # Periodic recovery will pick this delivery up without exposing its URL or headers.
        logger.error('Unable to dispatch application webhook delivery %s.', delivery_id)


def _finish(delivery, result, reason):
    from accounts.models import ApplicationAudit
    delivery.status = result
    delivery.save(update_fields=['status'])
    delivery.attempts.filter(result='pending').update(result='failed', reason=reason[:128])
    ApplicationAudit.objects.filter(id=delivery.audit_id).update(result=result, summary=reason)


def _claim_webhook(delivery_id):
    from accounts.models import ApplicationEventAttempt, ApplicationEventDelivery

    now = timezone.now()
    with transaction.atomic():
        delivery = ApplicationEventDelivery.objects.select_for_update().filter(
            id=delivery_id,
            method__in=('POST', 'PUT', 'PATCH'), status='pending',
        ).first()
        if not delivery:
            return None
        if delivery.expires_at <= now:
            _finish(delivery, 'failed', 'Webhook delivery deadline reached.')
            return None
        if delivery.available_at > now:
            return None
        previous = delivery.attempts.order_by('-number').first()
        number = previous.number + 1 if previous else 1
        if previous and previous.result == 'pending':
            previous.result = 'failed'
            previous.reason = 'Webhook worker interrupted.'
            previous.save(update_fields=['result', 'reason'])
        if number > WEBHOOK_ATTEMPT_LIMIT:
            _finish(delivery, 'failed', 'Webhook retry limit reached.')
            return None
        attempt = ApplicationEventAttempt.objects.create(delivery=delivery, number=number)
        delivery.available_at = min(
            delivery.expires_at, now + timedelta(seconds=WEBHOOK_CLAIM_LEASE),
        )
        delivery.save(update_fields=['available_at'])
        return {
            'attempt_id': attempt.id,
            'delivery_id': delivery.id,
            'event_id': delivery.event_id,
            'method': delivery.method,
            'url': delivery.url,
            'headers': delivery.headers,
            'body': delivery.body,
        }


def _complete_webhook(attempt_id, status_code=None, reason='', retryable=True):
    from accounts.models import ApplicationAudit, ApplicationEventAttempt, ApplicationEventDelivery

    now = timezone.now()
    with transaction.atomic():
        attempt = ApplicationEventAttempt.objects.filter(id=attempt_id).first()
        if not attempt:
            return
        delivery = ApplicationEventDelivery.objects.select_for_update().get(id=attempt.delivery_id)
        attempt.refresh_from_db()
        if attempt.result != 'pending' or delivery.status != 'pending':
            return
        if delivery.expires_at <= now:
            attempt.result = 'failed'
            attempt.reason = 'Webhook delivery deadline reached.'
            attempt.save(update_fields=['result', 'reason'])
            _finish(delivery, 'failed', attempt.reason)
            return
        success = status_code is not None and 200 <= status_code < 300
        attempt.result = 'success' if success else 'failed'
        attempt.status_code = status_code
        attempt.reason = '' if success else (reason or 'Webhook returned a non-2xx response.')
        attempt.save(update_fields=['result', 'status_code', 'reason'])
        if success:
            _finish(delivery, 'success', 'Webhook delivered.')
            return
        if not retryable or attempt.number >= WEBHOOK_ATTEMPT_LIMIT:
            _finish(delivery, 'failed', attempt.reason)
            return
        delay = WEBHOOK_RETRY_DELAYS[attempt.number - 1]
        delivery.available_at = min(delivery.expires_at, now + timedelta(seconds=delay))
        delivery.save(update_fields=['available_at'])
        ApplicationAudit.objects.filter(id=delivery.audit_id).update(
            result='retrying', summary='Webhook failed; waiting for retry.',
        )
        transaction.on_commit(
            lambda: dispatch_application_webhook(delivery.id, delivery.org_id, delay)
        )


@shared_task(soft_time_limit=15, time_limit=20)
def deliver_application_webhook(delivery_id, org_id):
    from accounts.credential_client.webhook_delivery import WebhookRequestError, send_webhook

    with tmp_to_org(org_id):
        claimed = _claim_webhook(delivery_id)
        if not claimed:
            return
        try:
            status_code = send_webhook(
                claimed['method'], claimed['url'], claimed['headers'], claimed['body'],
                delivery_id=claimed['delivery_id'], event_id=claimed['event_id'],
            )
        except WebhookRequestError as error:
            _complete_webhook(
                claimed['attempt_id'], reason=error.reason, retryable=error.retryable,
            )
        except Exception:
            logger.error('Application webhook delivery %s failed.', delivery_id)
            _complete_webhook(claimed['attempt_id'], reason='Webhook request failed.')
        else:
            _complete_webhook(claimed['attempt_id'], status_code=status_code)


@shared_task
@register_as_period_task(interval=60)
def expire_application_event_deliveries():
    from accounts.models import ApplicationEventDelivery
    now = timezone.now()
    with tmp_to_root_org():
        with transaction.atomic():
            deliveries = ApplicationEventDelivery.objects.select_for_update().filter(
                status='pending', expires_at__lte=now,
            )
            for delivery in deliveries.iterator():
                delivery.attempts.filter(result='pending').update(
                    result='failed', reason='Delivery deadline reached.',
                )
                _finish(delivery, 'failed', 'Notification delivery deadline reached.')
            recovery = list(ApplicationEventDelivery.objects.filter(
                method__in=('POST', 'PUT', 'PATCH'),
                status='pending',
                available_at__lte=now, expires_at__gt=now,
            ).values_list('id', 'org_id'))
        for delivery_id, org_id in recovery:
            dispatch_application_webhook(delivery_id, org_id)


@shared_task(
    verbose_name=_('Clean application records'),
    description=_('Clean expired application audits and completed webhook delivery records.'),
)
@register_as_period_task(crontab=CRONTAB_AT_AM_THREE)
def clean_application_records_period():
    from accounts.models import ApplicationAudit, ApplicationEventAttempt, ApplicationEventDelivery

    days = get_log_keep_day('APPLICATION_RECORD_KEEP_DAYS')
    expired_at = timezone.now() - timedelta(days=days)
    with tmp_to_root_org():
        delivery_counts = _delete_in_batches(ApplicationEventDelivery.objects.filter(
            date_created__lt=expired_at,
            status__in=('success', 'failed'),
        ))
        audit_counts = _delete_in_batches(ApplicationAudit.objects.filter(
            date_created__lt=expired_at,
            deliveries__isnull=True,
            delivery__isnull=True,
        ))

    logger.info(
        'Cleaned application records older than %s days: audits=%s, deliveries=%s, attempts=%s.',
        days,
        audit_counts.get(ApplicationAudit._meta.label, 0),
        delivery_counts.get(ApplicationEventDelivery._meta.label, 0),
        delivery_counts.get(ApplicationEventAttempt._meta.label, 0),
    )
