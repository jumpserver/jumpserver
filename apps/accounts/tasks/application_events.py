from celery import shared_task
from django.db import transaction
from django.utils import timezone

from ops.celery.decorator import register_as_period_task
from orgs.utils import tmp_to_root_org


@shared_task
@register_as_period_task(interval=60)
def expire_application_event_deliveries():
    from accounts.models import ApplicationEventDelivery
    from accounts.credential_client.events import ClientEventManager
    with tmp_to_root_org(), transaction.atomic():
        deliveries = ApplicationEventDelivery.objects.select_for_update().filter(
            status='pending', expires_at__lte=timezone.now(),
        )
        for delivery in deliveries.iterator():
            delivery.attempts.filter(result='pending').update(result='failed', reason='Delivery deadline reached.')
            ClientEventManager._finish(delivery, 'failed', 'Notification delivery deadline reached.')
