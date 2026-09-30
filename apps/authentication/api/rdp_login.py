"""Host-bound RDP credentials for the Tinker credential provider v2."""
import base64
import hashlib
import secrets
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.const import ConnectionTokenType
from authentication.models import ConnectionToken
from authentication.serializers import ConnectionTokenSecretSerializer
from authentication.serializers.connect_token_secret import _ConnectionTokenUserSerializer
from authentication.services.connection_token import get_connection_token_secret
from authentication.services.rdp_login import RDPLoginTicket, RDPLoginTicketCache
from authentication.serializers.rdp_login import RDPLoginRedeemSerializer
from common.permissions import IsServiceAccount
from orgs.utils import tmp_to_root_org
from perms.const import ActionChoices
from terminal.models import Applet, AppletHost
from terminal.const import TINKER_MIN_VERSION
from terminal.utils.tinker import get_tinker_upgrade_message


ticket_cache = RDPLoginTicketCache()


def digest(value):
    return hashlib.sha256(value.encode('ascii')).hexdigest()


def check_connection(token):
    token.is_valid(include_personal_secret=False)
    if token.type != ConnectionTokenType.USER:
        raise PermissionDenied('Only user connection tokens support RDP token login')
    if token.face_monitor_token:
        raise PermissionDenied('Direct RDP token login does not support face monitoring')
    # Recheck even when is_valid takes its recent-token shortcut.
    account = token.get_permed_account()
    if (not account or account.date_expired <= timezone.now()
            or not ActionChoices.contains(account.actions, ActionChoices.connect)):
        raise PermissionDenied('Connection permission is no longer valid')
    token.__dict__['permed_account'] = account
    method = token.connect_method_object or {}
    if method.get('type') != 'applet' or method.get('disabled'):
        raise PermissionDenied('An enabled Applet connection is required')
    return get_object_or_404(Applet, name=method.get('value'), is_active=True)


def check_host(host, applet, user=None):
    if not host.is_active or not host.terminal or host.terminal.type != 'tinker':
        raise PermissionDenied('A Tinker component must be bound to this host')
    upgrade_message = get_tinker_upgrade_message(host.tinker_version)
    if upgrade_message:
        raise PermissionDenied(upgrade_message)
    available = applet.filter_available_hosts() or []
    if not any(item.id == host.id for item in available):
        raise PermissionDenied('Applet is not available on this host')
    if user is not None:
        if (not user.is_service_account or host.terminal.user_id != user.id
                or not user.has_perm('authentication.view_superconnectiontokensecret')):
            raise PermissionDenied('This component is not authorized for the host')


def check_binding(ticket, token, applet, user):
    if (ticket.user_id != token.user_id or str(ticket.org_id) != str(token.org_id)
            or ticket.asset_id != token.asset_id
            or ticket.app_id != applet.id or ticket.app_name != applet.name):
        raise PermissionDenied('The connection authorization has changed')
    host = get_object_or_404(AppletHost, id=ticket.host_id)
    check_host(host, applet, user)


def is_tinker(user):
    terminal = getattr(user, 'terminal', None)
    return user.is_service_account and terminal and terminal.type == 'tinker'


def private_response(data):
    response = Response(data)
    response['Cache-Control'] = 'no-store'
    response['Pragma'] = 'no-cache'
    return response


def issue_applet_ticket(token):
    """Build the existing applet-option payload while its token row is locked."""
    applet = check_connection(token)
    host = applet.select_host(token.user, token.asset)
    if host is None:
        raise PermissionDenied(_(
            'No compatible Applet host is available. Upgrade and redeploy '
            'an applet host with Tinker %(minimum)s or later.'
        ) % {'minimum': TINKER_MIN_VERSION})
    check_host(host, applet)
    expires = min(token.date_expired, token.permed_account.date_expired,
                  timezone.now() + timedelta(minutes=5))
    password = secrets.token_urlsafe(32)
    for _ in range(3):
        username = 'jlt_' + base64.b32encode(secrets.token_bytes(10)).decode().lower()
        ticket = RDPLoginTicket(
            id=uuid4(), connection_id=uuid4(), connection_token_id=token.id,
            org_id=token.org_id, user_id=token.user_id, asset_id=token.asset_id,
            host_id=host.id, app_id=applet.id, app_name=applet.name,
            username=username, password_hash=digest(username + '\0' + password), expires_at=expires,
        )
        if ticket_cache.add(ticket):
            break
    else:
        raise PermissionDenied('Unable to issue an RDP login credential')
    # A transport credential, never a Core-managed or real Windows account.
    account = SimpleNamespace(
        id=ticket.id, name=username, full_username=username,
        secret=password, secret_type='password', privileged=False,
    )
    return {
        'id': str(ticket.id), 'applet': applet, 'host': host, 'account': account,
        'gateway': host.zone.select_gateway() if host.zone else None,
        'platform': host.platform, 'remote_app_option': token.get_remote_app_option(),
    }


class RDPLoginRedeemApi(APIView):
    permission_classes = [IsServiceAccount]
    serializer_class = RDPLoginRedeemSerializer

    @transaction.atomic
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with tmp_to_root_org():
            cached = ticket_cache.get(data['username'])
            if cached is None:
                raise PermissionDenied('Invalid or expired RDP login authorization')
            ticket, encoded = cached
            token = get_object_or_404(
                ConnectionToken.objects.select_for_update(), id=ticket.connection_token_id,
            )
            now = timezone.now()
            password_hash = digest(data['username'] + '\0' + data['password'])
            if (ticket.expires_at <= now
                    or not secrets.compare_digest(ticket.password_hash, password_hash)):
                raise PermissionDenied('Invalid or expired RDP login authorization')
            applet = check_connection(token)
            check_binding(ticket, token, applet, request.user)
            # The ticket/token deadline only governs this exchange. Once it
            # succeeds, local login and launch use the asset permission expiry.
            deadline = token.permed_account.date_expired
            if not ticket_cache.consume(data['username'], encoded):
                raise PermissionDenied('RDP login ticket has already been used')
            # The ticket is consumed before secrets are disclosed. An uncertain
            # outcome requires a new connection; it never reopens this ticket.
            connection = get_connection_token_secret(
                request, token, ConnectionTokenSecretSerializer, rdp_login=True,
            )
            return private_response({
                'attempt_id': str(ticket.id), 'connection_id': str(ticket.connection_id),
                'token_id': str(token.id), 'org_id': str(ticket.org_id),
                'host_id': str(ticket.host_id), 'user': _ConnectionTokenUserSerializer(token.user).data,
                'app_id': str(ticket.app_id), 'app_name': ticket.app_name,
                'target_asset_id': str(ticket.asset_id), 'connection': connection,
                'launch_deadline': deadline.isoformat(),
            })
