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
    items[user.id].append({
        'credential_type': credential_type,
        'identifier': str(identifier) if identifier else '-',
        'date_created': created,
        'date_last_used': used,
    })


@shared_task(
    verbose_name=_('Send credential activity summary'),
    description=_('Send users a summary of credential creation and successful use in the past 24 hours'),
)
@register_as_period_task(crontab=CRONTAB_AT_AM_TEN)
@tmp_to_root_org()
def send_credential_activity_summary():
    start = timezone.now() - datetime.timedelta(hours=24)
    items = defaultdict(list)
    users = {}

    for key in AccessKey.objects.filter(
            Q(date_created__gte=start) | Q(date_last_used__gte=start)
    ).select_related('user'):
        users[key.user_id] = key.user
        _add_activity(items, key.user, 'access_key', key.id,
                      key.date_created, key.date_last_used, start)

    for key in Passkey.objects.filter(
            Q(date_created__gte=start) | Q(date_last_used__gte=start)
    ).select_related('user'):
        users[key.user_id] = key.user
        _add_activity(items, key.user, 'passkey', key.id,
                      key.date_created, key.date_last_used, start)

    for token in PrivateToken.objects.filter(
            Q(created__gte=start) | Q(date_last_used__gte=start)
    ).select_related('user'):
        users[token.user_id] = token.user
        _add_activity(items, token.user, 'private_token', '',
                      token.created, token.date_last_used, start)

    temp_tokens = list(TempToken.objects.filter(
        Q(date_created__gte=start) | Q(date_verified__gte=start)
    ))
    temp_users = {
        user.username: user for user in User.objects.filter(
            username__in={token.username for token in temp_tokens}
        )
    }
    for token in temp_tokens:
        user = temp_users.get(token.username)
        if user:
            users[user.id] = user
        _add_activity(items, user, 'temp_token', token.id,
                      token.date_created, token.date_verified, start)

    for token in ConnectionToken.objects.filter(
            Q(date_created__gte=start) | Q(date_last_used__gte=start),
            user__isnull=False,
    ).select_related('user'):
        users[token.user_id] = token.user
        # The full ID is an authentication credential for bootstrap APIs.
        identifier = f'{str(token.id)[:8]}...{str(token.id)[-4:]}'
        _add_activity(items, token.user, 'connection_token', identifier,
                      token.date_created, token.date_last_used, start)

    AccessToken = get_access_token_model()
    for token in AccessToken.objects.filter(
            Q(created__gte=start) | Q(updated__gte=start),
            user__isnull=False,
    ).select_related('user'):
        users[token.user_id] = token.user
        used = token.updated if token.updated > token.created else None
        _add_activity(items, token.user, 'access_token', token.id,
                      token.created, used, start)

    for user_id, user_items in items.items():
        user_items.sort(
            key=lambda item: item['date_last_used'] or item['date_created'],
            reverse=True,
        )
        CredentialActivityDigestMessage(users[user_id], user_items).publish_async()


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
    from oauth2_provider.models import clear_expired
    clear_expired()
