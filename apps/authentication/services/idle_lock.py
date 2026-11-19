from django.conf import settings
from django.core.cache import cache
from django.db.models import IntegerField, Q
from django.db.models.functions import Cast

from users.models import Preference


IDLE_LOCK_SETTINGS = {
    'web_idle_lock_time': 'SECURITY_WEB_IDLE_LOCK_TIME',
    'client_idle_lock_time': 'SECURITY_CLIENT_IDLE_LOCK_TIME',
}
TIME_SETTINGS = {**IDLE_LOCK_SETTINGS, 'client_max_session_time': 'SECURITY_CLIENT_MAX_SESSION_TIME'}
PERSONAL_SETTINGS = (*TIME_SETTINGS, 'client_reauth_on_exit')
IDLE_LOCK_CATEGORY = 'security'
IDLE_LOCK_LIMITS_CACHE_KEY = 'idle-lock-limits:v1'


def idle_lock_limits(*, use_cache=False):
    if use_cache:
        limits = cache.get(IDLE_LOCK_LIMITS_CACHE_KEY)
        if limits is not None:
            return limits
    from settings.models import Setting

    values = {name: getattr(settings, name) for name in TIME_SETTINGS.values()}
    for item in Setting.objects.filter(name__in=values):
        values[item.name] = item.cleaned_value
    limits = {key: int(values[name]) for key, name in TIME_SETTINGS.items()}
    if use_cache:
        cache.set(IDLE_LOCK_LIMITS_CACHE_KEY, limits, timeout=60)
    return limits


def personal_idle_lock_time(user_id, name):
    value = Preference.objects.filter(
        user_id=user_id, category=IDLE_LOCK_CATEGORY, name=name,
    ).values_list('value', flat=True).first()
    return int(value) if value is not None else None


def effective_idle_lock_time(maximum, personal):
    if maximum == 0:
        return personal or 0
    return maximum if personal in (None, 0) else min(personal, maximum)


def personal_client_login_policy(user_id, policy, *, preferences=None):
    if preferences is None:
        preferences = dict(Preference.objects.filter(
            user_id=user_id, category=IDLE_LOCK_CATEGORY, name__in=PERSONAL_SETTINGS,
        ).values_list('name', 'value'))
    result = dict(policy)
    for field, name in (('idle_lock_time', 'client_idle_lock_time'),
                        ('max_session_time', 'client_max_session_time')):
        personal = int(preferences[name]) if name in preferences else None
        result[field] = effective_idle_lock_time(policy[field], personal)
        result[field + '_limit'] = policy[field]
        result[field + '_user'] = personal
    personal = bool(int(preferences['client_reauth_on_exit'])) if 'client_reauth_on_exit' in preferences else None
    result.update(reauth_on_exit=policy['reauth_on_exit'] or bool(personal),
                  reauth_on_exit_required=policy['reauth_on_exit'], reauth_on_exit_user=personal)
    return result


def idle_lock_preferences(user_id):
    from authentication.services.client_login_session import client_login_policy

    policy = personal_client_login_policy(user_id, client_login_policy(use_cache=False))
    web_maximum = idle_lock_limits()['web_idle_lock_time']
    web_personal = personal_idle_lock_time(user_id, 'web_idle_lock_time')
    return {
        'web_idle_lock_time': web_personal,
        'web_idle_lock_limit': web_maximum,
        'effective_web_idle_lock_time': effective_idle_lock_time(web_maximum, web_personal),
        'client_idle_lock_time': policy['idle_lock_time_user'],
        'client_idle_lock_limit': policy['idle_lock_time_limit'],
        'effective_client_idle_lock_time': policy['idle_lock_time'],
        'client_max_session_time': policy['max_session_time_user'],
        'client_max_session_limit': policy['max_session_time_limit'],
        'effective_client_max_session_time': policy['max_session_time'],
        'client_reauth_on_exit': policy['reauth_on_exit_user'],
        'client_reauth_on_exit_required': policy['reauth_on_exit_required'],
        'effective_client_reauth_on_exit': policy['reauth_on_exit'],
        'client_login_policy': policy,
    }


def clamp_idle_lock_preferences(setting_name, maximum):
    if maximum <= 0:
        return
    for name, setting in TIME_SETTINGS.items():
        if setting == setting_name:
            # Values are normalized non-negative integers written by the personal API.
            Preference.objects.filter(category=IDLE_LOCK_CATEGORY, name=name).alias(
                minutes=Cast('value', IntegerField()),
            ).filter(Q(minutes__gt=maximum) | Q(minutes=0)).update(value=str(maximum))
            break
