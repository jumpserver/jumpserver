from dataclasses import dataclass
from datetime import datetime, timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


EXPIRE_SOON_NOTICE_RELATED_FIELDS = {
    'date_expired',
    'expire_soon_notice_minutes',
}


@dataclass(frozen=True)
class ExpireSoonNoticeState:
    minutes: int | None
    notice_at: datetime | None


def get_expire_soon_notice_state(date_expired, minutes, now=None, allow_past=False):
    if minutes is None:
        return ExpireSoonNoticeState(None, None)
    if date_expired is None:
        raise ValidationError({'date_expired': _('This field is required.')})
    if minutes <= 0:
        raise ValidationError({
            'expire_soon_notice_minutes': _('Ensure this value is greater than 0.')
        })
    now = now or timezone.now()
    remaining_seconds = (date_expired - now).total_seconds()
    if minutes * 60 >= remaining_seconds:
        if allow_past:
            return ExpireSoonNoticeState(minutes, None)
        raise ValidationError({
            'expire_soon_notice_minutes': _('The notice time must be in the future.')
        })
    notice_at = date_expired - timedelta(minutes=minutes)
    return ExpireSoonNoticeState(minutes, notice_at)


def sync_expire_soon_notice(
        instance, attrs, *, now=None, allow_past=False, disable_if_past=False
):
    """Normalize persistable expiration-soon notice values."""
    is_create = instance is None

    def current(name, default=None):
        return getattr(instance, name, default) if instance is not None else default

    related_changed = is_create or any(
        name in attrs and attrs[name] != current(name)
        for name in EXPIRE_SOON_NOTICE_RELATED_FIELDS
    )
    if not related_changed:
        return attrs

    date_expired = attrs.get('date_expired', current('date_expired'))
    minutes = attrs.get(
        'expire_soon_notice_minutes',
        current('expire_soon_notice_minutes')
    )
    state = get_expire_soon_notice_state(
        date_expired, minutes, now=now, allow_past=allow_past
    )
    minutes = state.minutes
    if disable_if_past and state.notice_at is None:
        minutes = None
    attrs['expire_soon_notice_minutes'] = minutes
    attrs['expire_soon_notice_at'] = state.notice_at
    attrs['expire_soon_notice_sent_at'] = None
    return attrs


def sync_ticket_expire_soon_notice(
        instance, attrs, *, now=None, allow_past=False
):
    def current(name, default=None):
        return getattr(instance, name, default) if instance is not None else default

    date_expired = attrs.get('apply_date_expired', current('apply_date_expired'))
    minutes = attrs.get(
        'apply_expire_soon_notice_minutes',
        current('apply_expire_soon_notice_minutes')
    )
    state = get_expire_soon_notice_state(
        date_expired, minutes, now=now, allow_past=allow_past
    )
    attrs['apply_expire_soon_notice_minutes'] = state.minutes
    return attrs
