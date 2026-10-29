# -*- coding: utf-8 -*-
#
import datetime
import logging
from collections import defaultdict

from celery import shared_task
from django.conf import settings
from django.contrib.sessions.models import Session
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from oauth2_provider.models import get_access_token_model

from authentication.models import AccessKey, ConnectionToken, Passkey, PrivateToken, TempToken
from authentication.notifications import CredentialActivityDigestMessage
from common.const.crontab import CRONTAB_AT_AM_TEN, CRONTAB_AT_AM_TWO
from ops.celery.decorator import register_as_period_task
from orgs.utils import tmp_to_root_org
from users.models import User


def _recent(value, start):
    return value if value and value >= start else None


def _add_activity(items, user, credential_type, identifier, created, used, start):
    if not user or user.is_service_account:
        return
    created = _recent(created, start)
    used = _recent(used, start)
    if not created and not used:
        return
    activity = {
        'credential_type': credential_type,
        'identifier': str(identifier) if identifier else '-',
        'date_created': created,
        'date_last_used': used,
    }
    items[user.id].append(activity)
    return activity


def _credential_activity_queries(start):
    sources = (
        ('access_key', AccessKey, 'date_created', 'date_last_used', {}),
        ('passkey', Passkey, 'date_created', 'date_last_used', {}),
        ('private_token', PrivateToken, 'created', 'date_last_used', {}),
        ('temp_token', TempToken, 'date_created', 'date_verified', {}),
        ('connection_token', ConnectionToken, 'date_created', 'date_last_used', {
            'is_reusable': True, 'user__isnull': False,
        }),
        ('access_token', get_access_token_model(), 'created', 'updated', {
            'user__isnull': False,
        }),
    )
    return [
        (credential_type, model.objects.filter(
            Q(**{f'{created}__gte': start}) | Q(**{f'{used}__gte': start}),
            **filters,
        ), created, used)
        for credential_type, model, created, used, filters in sources
    ]


def _iter_activity_user_batches(sources, batch_size=100):
    recent_activity = Q(pk__in=[])
    for credential_type, queryset, __, ___ in sources:
        if credential_type == 'temp_token':
            recent_activity |= Q(username__in=queryset.order_by().values('username'))
        else:
            recent_activity |= Q(pk__in=queryset.order_by().values('user_id'))
    users = User.objects.filter(is_service_account=False).filter(recent_activity).only(
        'id', 'name', 'username', 'is_service_account',
    ).order_by('pk')
    last_pk = None
    while True:
        page = users if last_pk is None else users.filter(pk__gt=last_pk)
        batch = list(page[:batch_size])
        if not batch:
            return
        last_pk = batch[-1].pk
        yield batch
        if len(batch) < batch_size:
            return
        del batch


def _iter_credential_activity_rows(queryset, fields, *, cursor_field='pk', batch_size=500):
    # SQL LIMIT bounds mysqlclient's result buffer too. A private token's
    # primary key is its secret, so use its unique user_id as the cursor instead.
    selected = tuple(dict.fromkeys((cursor_field, *fields)))
    rows = queryset.order_by(cursor_field).values(*selected)
    cursor = None
    while True:
        page = rows
        if cursor is not None:
            page = rows.filter(**{f'{cursor_field}__gt': cursor[cursor_field]})
        batch = list(page[:batch_size])
        if not batch:
            return
        cursor = batch[-1]
        yield from batch
        if len(batch) < batch_size:
            return
        del batch


@shared_task(
    verbose_name=_('Send credential activity summary'),
    description=_('Send users a summary of credential creation and successful use in the past 24 hours'),
)
@register_as_period_task(crontab=CRONTAB_AT_AM_TEN)
@tmp_to_root_org()
def send_credential_activity_summary():
    start = timezone.now() - datetime.timedelta(hours=24)
    sources = _credential_activity_queries(start)
    category_order = {source[0]: index for index, source in enumerate(sources)}
    for user_batch in _iter_activity_user_batches(sources):
        users = {user.id: user for user in user_batch}
        users_by_name = {user.username: user for user in user_batch}
        items = defaultdict(list)
        for credential_type, queryset, created_field, used_field in sources:
            is_temporary = credential_type == 'temp_token'
            owner_field = 'username' if is_temporary else 'user_id'
            owner_values = users_by_name if is_temporary else users
            queryset = queryset.filter(**{f'{owner_field}__in': owner_values})
            cursor_field = 'user_id' if credential_type == 'private_token' else 'pk'
            fields = (owner_field, created_field, used_field)
            if credential_type == 'connection_token':
                fields += ('date_expired',)
            rows = _iter_credential_activity_rows(
                queryset, fields,
                cursor_field=cursor_field,
            )
            for row in rows:
                # SQL collations may match different username spellings. Keep
                # the old Python dictionary's exact match for temporary tokens.
                user = owner_values.get(row[owner_field])
                identifier = '' if credential_type == 'private_token' else row['pk']
                if credential_type == 'connection_token':
                    # The full ID is an authentication credential for bootstrap APIs.
                    identifier = f'{str(identifier)[:8]}...{str(identifier)[-4:]}'
                created, used = row[created_field], row[used_field]
                if credential_type == 'access_token' and used <= created:
                    used = None
                activity = _add_activity(items, user, credential_type, identifier, created, used, start)
                if activity is not None and credential_type == 'connection_token':
                    activity['_date_expired'] = row['date_expired']

        # Gather every category before publishing: each user still receives one
        # complete, sorted digest. Only this batch's activity stays in memory.
        for user in user_batch:
            user_items = items.pop(user.id, [])
            if not user_items:
                continue
            user_items.sort(
                key=lambda item: (
                    item['date_last_used'] or item['date_created'],
                    -category_order[item['credential_type']],
                    item.get('_date_expired', start),
                ),
                reverse=True,
            )
            # Preserve ConnectionToken's default ordering for equal activity
            # times without using its mutable expiry as a pagination cursor.
            for item in user_items:
                item.pop('_date_expired', None)
            CredentialActivityDigestMessage(user, user_items).publish_async()
        del users, users_by_name, owner_values, items, user_items, user_batch


@shared_task(
    verbose_name=_('Clean expired session'),
    description=_(
        "Since user logins create sessions, the system will clean up expired sessions every 24 hours"
    )
)
@register_as_period_task(interval=3600 * 24)
def clean_django_sessions():
    Session.objects.filter(expire_date__lt=timezone.now()).delete()


@shared_task(
    verbose_name=_('Clean expired temporary, connection tokens'),
    description=_(
        "When connecting to assets or generating temporary passwords, the system creates corresponding connection "
        "tokens or temporary credential records. To maintain security and manage storage, the system automatically "
        "deletes expired tokens every day at 2:00 AM based on the retention settings configured under System settings "
        "> Security > User password > Token Retention Period"
    )
)
@register_as_period_task(crontab=CRONTAB_AT_AM_TWO)
def clean_expire_token():
    logging.info('Cleaning expired temporary and connection tokens...')
    with tmp_to_root_org():
        now = timezone.now()
        days = settings.SECURITY_EXPIRED_TOKEN_RECORD_KEEP_DAYS
        expired_time = now - datetime.timedelta(days=days)
        count = ConnectionToken.objects.filter(date_expired__lt=expired_time).delete()
        logging.info('Deleted %d expired connection tokens.', count[0])
        count = TempToken.objects.filter(date_expired__lt=expired_time).delete()
        logging.info('Deleted %d temporary tokens.', count[0])
    logging.info('Cleaned expired temporary and connection tokens.')


@register_as_period_task(crontab=CRONTAB_AT_AM_TWO)
def clear_oauth2_provider_expired_tokens():
    """Reclaim obsolete credentials; request-time checks enforce login expiry."""
    from oauth2_provider.models import clear_expired
    from authentication.services.client_login_session import clear_client_login_sessions

    clear_client_login_sessions()
    clear_expired()
