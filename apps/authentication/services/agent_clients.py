"""Bounded maintenance of unused dynamic Agent OAuth clients."""
from datetime import timedelta

from django.db import transaction
from django.db.models import Exists, OuterRef
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from oauth2_provider.models import get_application_model
from redis.exceptions import RedisError

from authentication.backends.oauth2_provider.agent_registration import REGISTRATION_LOCK
from common.utils.lock import DistributedLock
from terminal.models import AgentApplication


class AgentClientCleanupBusy(Exception):
    pass


class AgentClientCleanupUnavailable(Exception):
    pass


def cleanup_agent_oauth_clients(*, older_than_days=7, limit=100, on_delete=None):
    if (type(older_than_days) is not int or not 1 <= older_than_days <= 3650
            or type(limit) is not int or not 1 <= limit <= 1000):
        raise ValueError('Use 1-3650 days and a limit of 1-1000 clients')

    cutoff = timezone.now() - timedelta(days=older_than_days)
    Application = get_application_model()
    relations = [
        relation for relation in Application._meta.related_objects
        if relation.related_model is not AgentApplication
    ]
    lock, acquired = None, False
    result = {'scanned': 0, 'deleted': 0, 'skipped': 0}
    try:
        lock = DistributedLock(REGISTRATION_LOCK, expire=60)
        acquired = lock.acquire(blocking=False)
        if not acquired:
            raise AgentClientCleanupBusy('Agent client registration is busy; retry later')

        candidates = Application.objects.filter(
            registration_source=Application.RegistrationSource.DCR, created__lt=cutoff,
            agent_registration__isnull=False, agent_registration__date_authorized__isnull=True,
        )
        # Exclude references before limiting the batch so retained clients cannot
        # permanently hide unused registrations. Base managers include all orgs.
        for relation in relations:
            references = relation.related_model._base_manager.filter(
                **{relation.field.name: OuterRef('pk')},
            )
            candidates = candidates.filter(~Exists(references))
        candidates = list(candidates.order_by('created', 'pk').values_list('pk', flat=True)[:limit])

        for pk in candidates:
            result['scanned'] += 1
            with transaction.atomic():
                # Authorization code issuance takes these locks in the same order.
                application = Application.objects.select_for_update().filter(
                    pk=pk, registration_source=Application.RegistrationSource.DCR, created__lt=cutoff,
                ).first()
                registration = None
                if application is not None:
                    registration = AgentApplication.objects.select_for_update().filter(
                        application=application, date_authorized__isnull=True,
                    ).first()
                if registration is None or any(
                    relation.related_model._base_manager.filter(**{relation.field.name: application}).exists()
                    for relation in relations
                ):
                    result['skipped'] += 1
                    continue
                if not lock.locked_by_me():
                    raise AgentClientCleanupBusy('Registration lock expired; retry cleanup')
                client = {'id': registration.pk, 'client_id': application.client_id, 'name': application.name}
                try:
                    with transaction.atomic():
                        application.delete()
                        if on_delete is not None:
                            on_delete(client)
                except ProtectedError:
                    result['skipped'] += 1
                    continue
                result['deleted'] += 1
    except RedisError as exc:
        raise AgentClientCleanupUnavailable('Registration coordination is unavailable') from exc
    finally:
        if acquired:
            try:
                lock.release()
            except RedisError:
                pass
    return result
