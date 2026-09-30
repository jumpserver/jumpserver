"""Host-bound RDP credentials for the Tinker credential provider v2."""
import base64
import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.const import ConnectionTokenType
from authentication.models import ConnectionToken, RDPLoginTicket
from authentication.serializers import ConnectionTokenSecretSerializer
from authentication.serializers.connect_token_secret import _ConnectionTokenUserSerializer
from authentication.serializers.rdp_login import (
    RDPLoginPrepareSerializer, RDPLoginRedeemSerializer, RDPLoginLaunchSerializer,
)
from common.permissions import IsServiceAccount, IsValidUser
from orgs.utils import tmp_to_root_org
from perms.const import ActionChoices
from terminal.models import Applet, AppletHost
from terminal.const import TINKER_MIN_VERSION
from terminal.utils.tinker import get_tinker_upgrade_message


def digest(value):
    return hashlib.sha256(value.encode('ascii')).hexdigest()


def check_connection(token, *, include_secret=False):
    token.is_valid(include_personal_secret=include_secret)
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


def check_legacy_secret_access(user):
    terminal = getattr(user, 'terminal', None)
    if user.is_service_account and terminal and terminal.type == 'tinker':
        raise PermissionDenied('Tinker requires an RDP launch authorization')


def private_response(data):
    response = Response(data)
    response['Cache-Control'] = 'no-store'
    response['Pragma'] = 'no-cache'
    return response


def lock_authorization(**lookup):
    # Keep the same lock order across prepare, redeem and launch.
    candidate = get_object_or_404(RDPLoginTicket, **lookup)
    token = get_object_or_404(
        ConnectionToken.objects.select_for_update(), id=candidate.connection_token_id,
    )
    ticket = get_object_or_404(
        RDPLoginTicket.objects.select_for_update(), **{**lookup, 'id': candidate.id},
    )
    return token, ticket


class RDPLoginPrepareApi(APIView):
    permission_classes = [IsValidUser]
    serializer_class = RDPLoginPrepareSerializer

    @transaction.atomic
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        lookup = {'id': serializer.validated_data['connection_token_id']}
        if request.user.is_service_account:
            # Use Core's existing privileged component authorization; never
            # accept client-supplied user, host or organization identities.
            terminal = getattr(request.user, 'terminal', None)
            if (not terminal or terminal.type != 'razor'
                    or not request.user.has_perm('authentication.view_superconnectiontokensecret')):
                raise PermissionDenied()
        else:
            if not request.user.has_perm('authentication.add_connectiontoken'):
                raise PermissionDenied()
            lookup['user'] = request.user
        with tmp_to_root_org():
            token = get_object_or_404(ConnectionToken.objects.select_for_update(), **lookup)
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
                try:
                    with transaction.atomic():
                        ticket = RDPLoginTicket.objects.create(
                            connection_token=token, org_id=token.org_id,
                            user_id=token.user_id, asset_id=token.asset_id,
                            host_id=host.id, app_id=applet.id, app_name=applet.name,
                            username=username, password_hash=digest(username + '\0' + password),
                            expires_at=expires,
                        )
                    break
                except IntegrityError:
                    if not RDPLoginTicket.objects.filter(username=username).exists():
                        raise
            else:
                raise PermissionDenied('Unable to issue an RDP login credential')
            return private_response({
                'attempt_id': str(ticket.id), 'connection_id': str(ticket.connection_id),
                'token_id': str(token.id),
                'host': {'id': str(host.id), 'address': host.address, 'port': host.get_protocol_port('rdp')},
                'credential': {
                    'mode': 'tinker_ticket_v2', 'domain': 'localhost',
                    'username': username, 'password': password, 'expires_at': expires.isoformat(),
                },
                'remote_app': {
                    'program': '||tinker',
                    'args': token.get_remote_app_option()['remoteapplicationcmdline:s'],
                },
            })


class RDPLoginRedeemApi(APIView):
    permission_classes = [IsServiceAccount]
    serializer_class = RDPLoginRedeemSerializer

    @transaction.atomic
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with tmp_to_root_org():
            token, ticket = lock_authorization(username=data['username'])
            now = timezone.now()
            password_hash = digest(data['username'] + '\0' + data['password'])
            if (ticket.redeemed_at or ticket.expires_at <= now
                    or not secrets.compare_digest(ticket.password_hash, password_hash)):
                raise PermissionDenied('Invalid or expired RDP login authorization')
            applet = check_connection(token)
            check_binding(ticket, token, applet, request.user)
            grant = 'jmsg2_' + secrets.token_urlsafe(32)
            ticket.redeemed_at = now
            ticket.redeemed_by_id = request.user.id
            ticket.redemption_id = data['redemption_id']
            ticket.broker_instance_id = data['broker_instance_id']
            ticket.windows_session_id = data['windows_session_id']
            ticket.grant_hash = digest(grant)
            deadline = min(token.date_expired, token.permed_account.date_expired)
            ticket.login_deadline = min(deadline, now + timedelta(seconds=90))
            ticket.launch_deadline = min(deadline, now + timedelta(minutes=5))
            try:
                with transaction.atomic():
                    ticket.save(update_fields=[
                        'redeemed_at', 'redeemed_by_id', 'redemption_id', 'broker_instance_id',
                        'windows_session_id', 'grant_hash', 'login_deadline', 'launch_deadline',
                    ])
            except IntegrityError:
                raise PermissionDenied('RDP login context has already been used')
            return private_response({
                'attempt_id': str(ticket.id), 'connection_id': str(ticket.connection_id),
                'token_id': str(token.id), 'org_id': str(ticket.org_id),
                'host_id': str(ticket.host_id), 'user': _ConnectionTokenUserSerializer(token.user).data,
                'app_id': str(ticket.app_id), 'app_name': ticket.app_name,
                'target_asset_id': str(ticket.asset_id), 'launch_grant': grant,
                'login_deadline': ticket.login_deadline.isoformat(),
                'launch_deadline': ticket.launch_deadline.isoformat(),
            })


class RDPLoginLaunchApi(APIView):
    permission_classes = [IsServiceAccount]
    serializer_class = RDPLoginLaunchSerializer

    @transaction.atomic
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with tmp_to_root_org():
            token, ticket = lock_authorization(id=data['attempt_id'])
            now = timezone.now()
            if (not ticket.redeemed_at or ticket.launched_at
                    or not ticket.launch_deadline or ticket.launch_deadline <= now
                    or not ticket.grant_hash
                    or not secrets.compare_digest(ticket.grant_hash, digest(data['launch_grant']))
                    or ticket.connection_token_id != data['token_id']
                    or ticket.connection_id != data['connection_id']
                    or ticket.redeemed_by_id != request.user.id
                    or ticket.broker_instance_id != data['broker_instance_id']
                    or ticket.windows_session_id != data['windows_session_id']):
                raise PermissionDenied('Invalid or expired launch authorization')
            applet = check_connection(token, include_secret=True)
            check_binding(ticket, token, applet, request.user)
            if getattr(token.account_object, 'secret_type', '') == 'ssh_certificate':
                raise PermissionDenied('SSH certificates are not supported by direct RDP token login')
            connection = ConnectionTokenSecretSerializer(token).data
            if not (token.is_reusable and settings.CONNECTION_TOKEN_REUSABLE
                    and not token.personal_credential_id):
                token.expire()
            ConnectionToken.objects.filter(pk=token.pk).update(date_last_used=now)
            ticket.launched_at = now
            ticket.request_id = data['request_id']
            ticket.local_sid = data['local_sid']
            ticket.logon_id = data['logon_id']
            ticket.grant_hash = None
            ticket.save(update_fields=['launched_at', 'request_id', 'local_sid', 'logon_id', 'grant_hash'])
            if token.personal_credential_id:
                from accounts.personal_credentials import record_personal_credential_audit
                record_personal_credential_audit(
                    operation='use', result='success', user=token.user, asset=token.asset,
                    credential_id=token.personal_credential_id, username=token.input_username,
                    secret_type=token.input_secret_type, remote_addr=token.remote_addr,
                    org_id=token.org_id,
                )
            return private_response({
                'attempt_id': str(ticket.id), 'app_id': str(ticket.app_id),
                'app_name': ticket.app_name, 'connection': connection,
            })
