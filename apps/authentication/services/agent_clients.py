"""Lifecycle and per-user limits for Agent OAuth clients."""
from datetime import timedelta

from django.db import transaction
from django.db.models import Exists, OuterRef
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from django.utils.translation import gettext as _
from oauth2_provider.models import (
    get_access_token_model, get_application_model, get_grant_model, get_id_token_model, get_refresh_token_model,
)
from redis.exceptions import RedisError

from common.utils.lock import DistributedLock
from terminal.models import AgentApplication, AgentOAuthBinding

REGISTRATION_LOCK = 'agent-oauth-client-registration'
MAX_USER_AGENT_CLIENTS = 10


def user_agent_client_limit_reached(user, client_id):
    clients = AgentOAuthBinding.objects.filter(user=user, application__agent_registration__isnull=False)
    if clients.filter(application__client_id=client_id).exists():
        return False
    client_ids = clients.values_list('application_id', flat=True).distinct()[:MAX_USER_AGENT_CLIENTS]
    return len(client_ids) >= MAX_USER_AGENT_CLIENTS


def user_agent_client_limit_message():
    return _('You can authorize up to %(limit)s MCP clients. Revoke an existing client in Personal settings > MCP clients before adding another.') % {
        'limit': MAX_USER_AGENT_CLIENTS,
    }


class AgentClientCleanupBusy(Exception):
    pass


class AgentClientCleanupUnavailable(Exception):
    pass


def revoke_user_agent_client(user, application, registration):
    """Revoke and recycle while the caller holds both identity row locks."""
    authorizations = (
        get_refresh_token_model(), get_access_token_model(), get_grant_model(), get_id_token_model(),
        AgentOAuthBinding,
    )
    for model in authorizations:
        model.objects.filter(user=user, application=application).delete()
    if any(model.objects.filter(application=application).exists() for model in authorizations):
        return False

    # Keep every referenced identity, including login-session history whose FK
    # would otherwise cascade. Base managers include audit rows in all orgs.
    referenced = any(
        relation.related_model._base_manager.filter(**{relation.field.name: application}).exists()
        for relation in application._meta.related_objects
        if relation.related_model is not AgentApplication
    )
    if not referenced:
        try:
            with transaction.atomic():
                application.delete()
            return True
        except ProtectedError:
            pass
    application.redirect_uris = ''
    application.save(update_fields=['redirect_uris'])
    registration.delete()
    return True


def cleanup_agent_oauth_clients(*, older_than_days=7, limit=100):
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
                try:
                    with transaction.atomic():
                        application.delete()
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
