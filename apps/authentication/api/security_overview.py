from datetime import timedelta

from django.conf import settings
from django.db.models import Count, Min, Q
from django.utils import timezone
from oauth2_provider.models import get_access_token_model
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from audits.models import UserSession
from authentication.backends.passkey.models import Passkey
from authentication.models import AccessKey, ConnectionToken, SSHKey, TempToken
from authentication.services.client_login_session import online_device_client_sessions
from common.permissions import IsValidUser
from common.sessions import session_login_policies
from orgs.models import Organization
from orgs.utils import get_current_org
from rbac.models import RoleBinding
from terminal.models import Session

__all__ = ['SecurityOverviewApi']


def get_workbench_org_ids(user):
    org = get_current_org()
    allowed_ids = {
        str(item.id) for item in RoleBinding.get_user_has_the_perm_orgs('rbac.view_workbench', user)
    }
    if str(org.id) not in allowed_ids:
        raise PermissionDenied()
    return allowed_ids - {Organization.ROOT_ID} if org.is_root() else {str(org.id)}


def get_login_session_summary(request):
    keys = UserSession.objects.filter(user=request.user).order_by().values_list('key', flat=True).distinct()
    web_sessions = session_login_policies(list(keys))
    client = getattr(request, 'client_login_session', None)
    # An idle client can still be signed in.
    clients = online_device_client_sessions().filter(user=request.user).aggregate(
        total=Count('pk'), current=Count('pk', filter=Q(pk=client.pk if client else None)),
    )
    total = len(web_sessions) + clients['total']
    current = int(request.session.session_key in web_sessions or clients['current'] > 0)
    return {'count': total, 'current': current, 'other': total - current}


class SecurityOverviewApi(APIView):
    """Personal metadata only. No caller-supplied user ID or credential values."""
    permission_classes = (IsValidUser,)
    unused_days = 90

    def get(self, request):
        user = request.user
        org_ids = get_workbench_org_ids(user)
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

        mfa_enabled = user.mfa_enabled
        mfa_ready = mfa_enabled and bool(user.active_mfa_backends)
        data = {
            'generated_at': now,
            'login_sessions': get_login_session_summary(request),
            'asset_sessions': {'count': Session.get_active_sessions().filter(
                user_id=str(user.pk), org_id__in=org_ids,
            ).count()},
            'access_keys': access_keys,
            'temp_tokens': temp_tokens,
            'connection_tokens': {'count': ConnectionToken.objects.filter(
                user=user, org_id__in=org_ids, is_active=True, is_reusable=True, date_expired__gt=now,
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
