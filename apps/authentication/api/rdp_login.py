"""Direct RemoteApp login; Windows runtime accounts remain local to tinkerd."""
import hashlib
import re
import secrets
from datetime import timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from authentication.const import ConnectionTokenType
from authentication.models import ConnectionToken, RDPLoginTicket
from authentication.serializers import ConnectionTokenSecretSerializer
from common.permissions import IsServiceAccount, IsValidUser
from orgs.utils import tmp_to_root_org
from perms.const import ActionChoices
from terminal.models import Applet, AppletHost


def digest(value):
    return hashlib.sha256(value.encode('ascii')).hexdigest()


def bearer(data, key, prefix):
    value = data.get(key, '')
    if not isinstance(value, str) or not re.fullmatch(prefix + r'[A-Za-z0-9_-]{43}', value):
        raise PermissionDenied('Invalid or expired RDP login authorization')
    return digest(value)


def check_connection(token):
    # Do not use is_valid's recent-token permission shortcut for this new login.
    token.is_valid(include_personal_secret=bool(token.personal_credential_id))
    if token.type != ConnectionTokenType.USER:
        raise PermissionDenied('Only user connection tokens support RDP token login')
    if token.face_monitor_token:
        raise PermissionDenied('Direct RDP token login does not support face monitoring')
    account = token.get_permed_account()
    if (not account or account.date_expired <= timezone.now()
            or not ActionChoices.contains(account.actions, ActionChoices.connect)):
        raise PermissionDenied('Connection permission is no longer valid')
    method = token.connect_method_object or {}
    if method.get('type') != 'applet' or method.get('disabled'):
        raise PermissionDenied('An enabled Applet connection is required')
    return get_object_or_404(Applet, name=method.get('value'), is_active=True)


def check_host(host, applet, user=None):
    if not host.is_active or host.deploy_options.get('RDP_TOKEN_LOGIN') is not True:
        raise PermissionDenied('RDP token login is not enabled on this host')
    available = applet.filter_available_hosts() or []
    if not any(item.id == host.id for item in available):
        raise PermissionDenied('Applet is not available on this host')
    if user is not None:
        if (not user.is_service_account or not host.terminal
                or host.terminal.user_id != user.id
                or not user.has_perm('authentication.view_superconnectiontokensecret')):
            raise PermissionDenied('This component is not authorized for the host')


def private_response(data):
    response = Response(data)
    response['Cache-Control'] = 'no-store'
    response['Pragma'] = 'no-cache'
    return response


def lock_authorization(**lookup):
    # All three endpoints lock the connection first, then its ticket. Re-read
    # the ticket after locking: issuance may have replaced an unconsumed one.
    candidate = get_object_or_404(RDPLoginTicket, **lookup)
    token = get_object_or_404(
        ConnectionToken.objects.select_for_update(), id=candidate.connection_token_id,
    )
    ticket = get_object_or_404(
        RDPLoginTicket.objects.select_for_update(), id=candidate.id, **lookup,
    )
    return token, ticket


class RDPLoginIssueApi(APIView):
    permission_classes = [IsValidUser]

    @transaction.atomic
    def post(self, request):
        if (request.user.is_service_account
                or not request.user.has_perm('authentication.add_connectiontoken')):
            raise PermissionDenied()
        field = serializers.UUIDField()
        token_id = field.run_validation(request.data.get('connection_token_id'))
        with tmp_to_root_org():
            token = get_object_or_404(
                ConnectionToken.objects.select_for_update(), id=token_id, user=request.user,
            )
            applet = check_connection(token)
            host = applet.select_host(token.user, token.asset, rdp_token_login=True)
            if host is None:
                raise PermissionDenied('No available Applet host')
            check_host(host, applet)
            previous = RDPLoginTicket.objects.filter(connection_token=token).first()
            if previous and previous.consumed_at:
                raise PermissionDenied('Create a new connection token to log in again')
            if previous:
                previous.delete()
            value = 'jms1_' + secrets.token_urlsafe(32)
            expires = min(token.date_expired, timezone.now() + timedelta(seconds=60))
            RDPLoginTicket.objects.create(
                connection_token=token, host_id=host.id, app_name=applet.name,
                ticket_hash=digest(value), expires_at=expires,
            )
            # No Account selection, creation, or Windows credentials in this API.
            return private_response({
                'ticket': value, 'expires_at': expires.isoformat(),
                'host_id': str(host.id), 'address': host.address,
                'port': host.get_protocol_port('rdp'), 'app_name': applet.name,
                'remote_app': '||tinker', 'remote_app_args': '--rdp-login',
            })


class RDPLoginRedeemApi(APIView):
    permission_classes = [IsServiceAccount]

    @transaction.atomic
    def post(self, request):
        ticket_hash = bearer(request.data, 'ticket', 'jms1_')
        with tmp_to_root_org():
            token, ticket = lock_authorization(ticket_hash=ticket_hash)
            now = timezone.now()
            if ticket.consumed_at or ticket.expires_at <= now:
                raise PermissionDenied('Invalid or expired RDP login authorization')
            applet = check_connection(token)
            host = get_object_or_404(AppletHost, id=ticket.host_id)
            check_host(host, applet, request.user)
            if applet.name != ticket.app_name:
                raise PermissionDenied('Applet has changed')
            grant = 'jmsg1_' + secrets.token_urlsafe(32)
            ticket.consumed_at = now
            ticket.grant_hash = digest(grant)
            ticket.grant_expires_at = min(token.date_expired, now + timedelta(seconds=90))
            ticket.save(update_fields=['consumed_at', 'grant_hash', 'grant_expires_at'])
            return private_response({
                'host_id': str(host.id), 'user_id': str(token.user_id),
                'app_name': ticket.app_name, 'grant': grant,
                'expires_at': ticket.grant_expires_at.isoformat(),
            })


class RDPLoginLaunchApi(APIView):
    permission_classes = [IsServiceAccount]

    @transaction.atomic
    def post(self, request):
        grant_hash = bearer(request.data, 'grant', 'jmsg1_')
        with tmp_to_root_org():
            token, ticket = lock_authorization(grant_hash=grant_hash)
            now = timezone.now()
            if (not ticket.consumed_at or ticket.launched_at
                    or not ticket.grant_expires_at or ticket.grant_expires_at <= now):
                raise PermissionDenied('Invalid or expired launch authorization')
            applet = check_connection(token)
            host = get_object_or_404(AppletHost, id=ticket.host_id)
            check_host(host, applet, request.user)
            if applet.name != ticket.app_name:
                raise PermissionDenied('Applet has changed')
            # Certificate issuance requires a client public key; don't silently
            # return an unusable credential through this first-version endpoint.
            if getattr(token.account_object, 'secret_type', '') == 'ssh_certificate':
                raise PermissionDenied('SSH certificates are not supported by direct RDP token login')
            data = ConnectionTokenSecretSerializer(token).data
            token.expire()
            ticket.launched_at = now
            ticket.save(update_fields=['launched_at'])
            if token.personal_credential_id:
                from accounts.personal_credentials import record_personal_credential_audit
                record_personal_credential_audit(
                    operation='use', result='success', user=token.user, asset=token.asset,
                    credential_id=token.personal_credential_id, username=token.input_username,
                    secret_type=token.input_secret_type, remote_addr=token.remote_addr,
                    org_id=token.org_id,
                )
            return private_response({'app_name': ticket.app_name, 'connection': data})
