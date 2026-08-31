from dataclasses import dataclass
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


SHORT_NOTICE_RELATED_FIELDS = {
    'date_start',
    'date_expired',
    'short_expire_notice_enabled',
    'short_expire_notice_minutes',
}


@dataclass(frozen=True)
class ShortExpireNoticeState:
    enabled: bool
    minutes: int | None
    notice_at: object | None


def get_short_expire_notice_state(
        date_start, date_expired, enabled, minutes, now=None
):
    if date_expired is None and not enabled:
        return ShortExpireNoticeState(False, None, None)
    if date_expired is None:
        raise ValidationError({'date_expired': _('This field is required.')})

    if not enabled:
        return ShortExpireNoticeState(False, minutes, None)

    if minutes is None:
        raise ValidationError({
            'short_expire_notice_minutes': _('This field is required.')
        })
    if minutes <= 0:
        raise ValidationError({
            'short_expire_notice_minutes': _('Ensure this value is greater than 0.')
        })
    notice_at = date_expired - timedelta(minutes=minutes)
    now = now or timezone.now()
    if notice_at <= now:
        raise ValidationError({
            'short_expire_notice_minutes': _('The notice time must be in the future.')
        })
    return ShortExpireNoticeState(True, minutes, notice_at)


def sync_short_expire_notice(
        instance, attrs, *, default_enabled=False, default_minutes=None, now=None
):
    """Normalize and persistable short-notice values in serializer/create attrs."""
    is_create = instance is None

    def current(name, default=None):
        return getattr(instance, name, default) if instance is not None else default

    related_changed = is_create or any(
        name in attrs and attrs[name] != current(name)
        for name in SHORT_NOTICE_RELATED_FIELDS
    )
    if not related_changed:
        return attrs

    date_start = attrs.get('date_start', current('date_start'))
    date_expired = attrs.get('date_expired', current('date_expired'))
    enabled = attrs.get(
        'short_expire_notice_enabled',
        default_enabled if is_create else current('short_expire_notice_enabled', False)
    )
    minutes = attrs.get(
        'short_expire_notice_minutes',
        default_minutes if is_create and enabled else current('short_expire_notice_minutes')
    )

    state = get_short_expire_notice_state(
        date_start, date_expired, enabled, minutes, now=now
    )
    attrs['short_expire_notice_enabled'] = state.enabled
    attrs['short_expire_notice_minutes'] = state.minutes
    attrs['short_expire_notice_at'] = state.notice_at
    attrs['short_expire_notice_sent_at'] = None
    return attrs


def sync_ticket_short_expire_notice(
        instance, attrs, *, default_enabled=False, default_minutes=None, now=None
):
    is_create = instance is None

    def current(name, default=None):
        return getattr(instance, name, default) if instance is not None else default

    date_start = attrs.get('apply_date_start', current('apply_date_start'))
    date_expired = attrs.get('apply_date_expired', current('apply_date_expired'))
    enabled = attrs.get(
        'apply_short_expire_notice_enabled',
        default_enabled if is_create else current('apply_short_expire_notice_enabled', False)
    )
    minutes = attrs.get(
        'apply_short_expire_notice_minutes',
        default_minutes if is_create and enabled else current('apply_short_expire_notice_minutes')
    )
    state = get_short_expire_notice_state(
        date_start, date_expired, enabled, minutes, now=now
    )
    attrs['apply_short_expire_notice_enabled'] = state.enabled
    attrs['apply_short_expire_notice_minutes'] = state.minutes
    return attrs
