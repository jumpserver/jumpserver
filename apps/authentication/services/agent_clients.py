"""Lifecycle and per-user limits for Agent OAuth clients."""
from collections import defaultdict
from datetime import timedelta

from django.db import transaction
from django.db.models import BooleanField, Case, Exists, F, OuterRef, Q, Subquery, Value, When
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from django.utils.translation import gettext as _
from oauth2_provider.models import (
    get_access_token_model, get_application_model, get_grant_model, get_id_token_model, get_refresh_token_model,
    refresh_token_expire_timedelta,
)
from redis.exceptions import RedisError

from common.utils.lock import DistributedLock
from terminal.models import AgentApplication, AgentOAuthBinding

REGISTRATION_LOCK = 'agent-oauth-client-registration'
MAX_USER_AGENT_CLIENTS = 10


def active_agent_refresh_tokens():
    tokens = get_refresh_token_model().objects.filter(revoked__isnull=True, access_token__isnull=False)
    lifetime = refresh_token_expire_timedelta()
    if lifetime:
        tokens = tokens.filter(access_token__expires__gt=timezone.now() - lifetime)
    return tokens


def agent_oauth_bindings():
    """The same credential lifetime rules drive personal lists and reclamation."""
    now = timezone.now()
    refresh = active_agent_refresh_tokens().filter(
        user_id=OuterRef('user_id'), application_id=OuterRef('application_id'),
        token_family=OuterRef('refresh_family'),
    )
    return AgentOAuthBinding.objects.annotate(has_refresh=Exists(refresh)).annotate(is_live=Case(
        When(
            Q(has_refresh=True)
            | Q(grant__expires__gt=now, grant__user_id=F('user_id'), grant__application_id=F('application_id'))
            | Q(access_token__expires__gt=now, access_token__user_id=F('user_id'),
                access_token__application_id=F('application_id'), access_token__refresh_token__revoked__isnull=True),
            then=Value(True),
        ),
        default=Value(False), output_field=BooleanField(),
    ))


def has_other_agent_authorizations(user_id, application_id):
    return agent_oauth_bindings().filter(application_id=application_id, is_live=True).exclude(user_id=user_id).exists()


def agent_authorization_conflict_message():
    return _('This MCP client is already authorized to another user. '
             'Revoke the previous authorization or register a new client before signing in.')


def cleanup_agent_oauth_bindings(*, limit=500):
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError('Use a limit of 1-1000 bindings')
    latest = AgentOAuthBinding.objects.filter(application_id=OuterRef('application_id')).order_by('-pk').values('pk')[:1]
    active = agent_oauth_bindings().filter(application_id=OuterRef('application_id'), is_live=True)
    candidates = agent_oauth_bindings().filter(is_live=False).annotate(
        has_active=Exists(active), latest_id=Subquery(latest),
    ).filter(Q(has_active=True) | ~Q(pk=F('latest_id'))).order_by('pk')
    grouped = defaultdict(list)
    for pk, application_id in candidates.values_list('pk', 'application_id')[:limit]:
        grouped[application_id].append(pk)
    result = {'scanned': sum(map(len, grouped.values())), 'deleted': 0}
    for application_id, pks in grouped.items():
        with transaction.atomic():
            # Token minting, consent and revocation acquire this identity lock first.
            if not get_application_model().objects.select_for_update().filter(pk=application_id).exists():
                continue
            stale = agent_oauth_bindings().filter(application_id=application_id, pk__in=pks, is_live=False)
            if not agent_oauth_bindings().filter(application_id=application_id, is_live=True).exists():
                # Retain the last user's personal client entry even after all credentials expire.
                last = AgentOAuthBinding.objects.filter(application_id=application_id).order_by('-pk').values_list(
                    'pk', flat=True,
                ).first()
                stale = stale.exclude(pk=last)
            result['deleted'] += stale.delete()[0]
    return result


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
