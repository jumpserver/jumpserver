from datetime import timedelta
from importlib import import_module

from django.conf import settings
from django.core.cache import caches
from django.db.models import Count, Min, Q
from django.utils import timezone
from oauth2_provider.models import get_access_token_model
from rest_framework.response import Response
from rest_framework.views import APIView

from audits.models import UserSession
from common.permissions import IsValidUser
from authentication.backends.passkey.models import Passkey
from authentication.models import AccessKey, ConnectionToken, SSHKey, TempToken
from terminal.models import Session

__all__ = ['SecurityOverviewApi']


def get_user_login_session_keys(user):
    """Check only this user's session keys; never scan the shared session cache."""
    keys = list(UserSession.objects.filter(user=user).order_by().values_list('key', flat=True).distinct())
    if not keys:
        return []
    store_class = import_module(settings.SESSION_ENGINE).SessionStore
    cache_keys = {key: store_class(session_key=key).cache_key for key in keys}
    live = caches[settings.SESSION_CACHE_ALIAS].get_many(cache_keys.values())
    return [key for key, cache_key in cache_keys.items() if live.get(cache_key)]


class SecurityOverviewApi(APIView):
    """Personal metadata only. No caller-supplied user ID or credential values."""
    permission_classes = (IsValidUser,)
    unused_days = 90

    def get(self, request):
        user = request.user
        now = timezone.now()
        cutoff = now - timedelta(days=self.unused_days)
        access_keys = AccessKey.objects.filter(user=user, is_active=True).aggregate(
            count=Count('pk'),
            unused_count=Count('pk', filter=(
                Q(date_last_used__lt=cutoff) |
                Q(date_last_used__isnull=True, date_created__lt=cutoff)
            )),
        )
        access_keys['unused_days'] = self.unused_days
        temp_tokens = TempToken.objects.filter(
            username=user.username, verified=False, date_expired__gt=now,
        ).aggregate(count=Count('pk'), next_expiry=Min('date_expired'))
        temp_tokens['enabled'] = settings.AUTH_TEMP_TOKEN

        sessions = get_user_login_session_keys(user)
        current = int(request.session.session_key in sessions)
        mfa_enabled = user.mfa_enabled
        mfa_ready = mfa_enabled and bool(user.active_mfa_backends)
        data = {
            'generated_at': now,
            'login_sessions': {
                'count': len(sessions), 'current': current,
                'other': len(sessions) - current,
            },
            'asset_sessions': {'count': Session.objects.filter(
                user_id=str(user.pk), is_finished=False,
            ).count()},
            'access_keys': access_keys,
            'temp_tokens': temp_tokens,
            # OrgManager keeps this aligned with the personal token management page.
            # This is a lifecycle count, not a claim that asset permissions remain valid.
            'connection_tokens': {'count': ConnectionToken.objects.filter(
                user=user, is_active=True, is_reusable=True, date_expired__gt=now,
            ).count()},
            'ssh_keys': {'count': SSHKey.objects.filter(user=user, is_active=True).count()},
            'passkeys': {
                'count': Passkey.objects.filter(user=user, is_active=True).count(),
                'enabled': settings.AUTH_PASSKEY,
            },
            'access_tokens': {'count': get_access_token_model().objects.filter(
                user=user, expires__gt=now,
            ).count()},
            'mfa': {'enabled': mfa_enabled, 'configured': mfa_ready},
        }
        response = Response(data)
        response['Cache-Control'] = 'no-store'
        return response
