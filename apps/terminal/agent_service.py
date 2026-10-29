"""Core-owned authorization and state transitions for the Agent executor.

OAuth tokens are accepted only by the component introspection endpoint. Signed
context and session capabilities are bound to the registered execution node.
They never replace the user's asset permission and connection ACL checks.
"""
import hashlib
import json
import uuid
from datetime import timedelta
from types import SimpleNamespace

from django.core import signing
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from oauth2_provider.models import get_access_token_model, get_refresh_token_model
from rest_framework.exceptions import PermissionDenied, ValidationError, APIException

from orgs.models import Organization
from orgs.utils import tmp_to_org, tmp_to_root_org
from terminal.models import AgentApplication, AgentOAuthBinding, AgentSession, AgentAction, AgentEvent
from users.models import User

SCOPE = 'agent:access'
CONTEXT_SALT = 'jumpserver.agent.context.v1'
SESSION_SALT = 'jumpserver.agent.session.v1'
CONTEXT_TTL = 300
SESSION_TTL = 7200
FINAL_STATES = frozenset(('succeeded', 'failed', 'rejected', 'expired', 'cancelled', 'unknown'))
ACTION_KINDS = frozenset((
    'execute_command', 'file_stat', 'file_list', 'file_read', 'file_write', 'file_upload',
    'file_download', 'file_mkdir', 'file_rename', 'file_remove',
    'open_terminal',
))
SUPPORTED_PROTOCOLS = frozenset(('ssh', 'sftp', 'mysql', 'mariadb', 'postgresql'))


class Conflict(APIException):
    status_code = 409
    default_code = 'agent_conflict'


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def require_keys(data, allowed, required=()):
    if not isinstance(data, dict) or set(data) - set(allowed):
        raise ValidationError('Unknown or invalid request fields')
    if any(key not in data for key in required):
        raise ValidationError('Missing required request fields')


def text_field(value, name, maximum=128, empty=False):
    if not isinstance(value, str) or len(value) > maximum or ('\x00' in value):
        raise ValidationError({name: 'Invalid value'})
    if not empty and not value.strip():
        raise ValidationError({name: 'This field is required'})
    return value


def identifier(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise ValidationError('Invalid identifier')


def integer(value, name, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValidationError({name: f'Expected an integer from {minimum} to {maximum}'})
    return value


def available_agent_organizations(user):
    organizations = Organization.objects.exclude(id__in=(Organization.ROOT_ID, Organization.SYSTEM_ID))
    if not user.is_valid:
        return organizations.none()
    if not user.is_superuser:
        organizations = organizations.filter(members=user)
    return organizations.distinct().order_by('name', 'id')


def check_agent_organization(user, org_id):
    org_id = str(identifier(org_id))
    if not available_agent_organizations(user).filter(pk=org_id).exists():
        raise PermissionDenied('Organization is not available to this user')
    return org_id


def token_organization_binding(token, refresh=None):
    bindings = AgentOAuthBinding.objects.filter(user_id=token.user_id, application_id=token.application_id)
    binding = bindings.filter(access_token=token).first()
    if binding:
        return binding
    if refresh and refresh.token_family:
        return bindings.filter(refresh_family=refresh.token_family).first()
    return None


def introspect(node, data):
    require_keys(data, ('access_token', 'resource', 'org_id'), ('access_token', 'resource'))
    raw = text_field(data['access_token'], 'access_token', 8192)
    token = get_access_token_model().objects.select_related('user', 'application').filter(
        token_checksum=hashlib.sha256(raw.encode()).hexdigest(),
    ).first()
    if not token or not token.is_valid([SCOPE]) or not token.user or not token.user.is_valid:
        raise PermissionDenied('Invalid or expired MCP token', code='invalid_token')
    resource = text_field(data['resource'], 'resource', 512)
    registration = AgentApplication.objects.filter(application=token.application, is_active=True).first()
    if not registration or registration.resource != resource or token.resource != [resource]:
        raise PermissionDenied('Token is not issued for this MCP resource', code='invalid_token')
    refresh = get_refresh_token_model().objects.filter(access_token=token).first()
    binding = token_organization_binding(token, refresh)
    if not binding:
        raise PermissionDenied('OAuth authorization has no organization binding')
    org_id = str(binding.org_id)
    if data.get('org_id') and str(identifier(data['org_id'])) != org_id:
        raise PermissionDenied('Organization does not match this OAuth authorization')
    check_agent_organization(token.user, org_id)
    if refresh and refresh.revoked is not None:
        raise PermissionDenied('OAuth authorization revoked')
    payload = {
        'user_id': str(token.user_id), 'application_id': token.application_id,
        'client_id': token.application.client_id, 'org_id': org_id,
        'token_id': token.pk, 'family': str(refresh.token_family) if refresh and refresh.token_family else '',
        'node_id': str(node.id), 'resource': resource,
    }
    expires = min(token.expires, timezone.now() + timedelta(seconds=CONTEXT_TTL))
    payload['expires'] = expires.timestamp()
    return {
        'user_id': payload['user_id'], 'org_id': org_id, 'client_id': payload['client_id'],
        'resource': resource, 'scopes': [SCOPE], 'expires_at': expires.isoformat(),
        'context_token': signing.dumps(payload, salt=CONTEXT_SALT),
    }


def context_identity(node, value):
    try:
        context = signing.loads(text_field(value, 'context_token', 8192), salt=CONTEXT_SALT, max_age=CONTEXT_TTL)
        if context['node_id'] != str(node.id) or context['expires'] <= timezone.now().timestamp():
            raise PermissionDenied('Execution context expired or belongs to another node')
        user = User.objects.get(pk=context['user_id'])
        check_agent_organization(user, context['org_id'])
        if not AgentApplication.objects.filter(
            application_id=context['application_id'], resource=context['resource'], is_active=True,
        ).exists():
            raise PermissionDenied('Agent application disabled')
        if not authority_exists(user.id, context['application_id'], context['token_id'], context['family']):
            raise PermissionDenied('OAuth authorization revoked')
        return context, user
    except (signing.BadSignature, User.DoesNotExist, KeyError, TypeError, ValueError):
        raise PermissionDenied('Invalid execution context')


def authority_exists(user_id, application_id, token_id, family):
    if family:
        return get_refresh_token_model().objects.filter(
            token_family=family, user_id=user_id, application_id=application_id, revoked__isnull=True,
        ).exists()
    return get_access_token_model().objects.filter(
        pk=token_id, user_id=user_id, application_id=application_id, expires__gt=timezone.now(),
    ).exists()


def session_capability(session):
    return signing.dumps({
        'session_id': str(session.id), 'node_id': str(session.terminal_id), 'capability': str(session.capability),
    }, salt=SESSION_SALT)


def owned_session(node, session_id, capability, *, lock=False, check=True):
    try:
        decoded = signing.loads(text_field(capability, 'session_token', 8192), salt=SESSION_SALT)
    except signing.BadSignature:
        raise PermissionDenied('Invalid session capability')
    with tmp_to_root_org():
        qs = AgentSession.objects.select_related('user', 'application', 'connection_token__asset', 'terminal_session')
        if lock:
            qs = qs.select_related(None).select_for_update()
        session = get_object_or_404(qs, pk=identifier(session_id), terminal=node)
    expected = {'session_id': str(session.id), 'node_id': str(node.id), 'capability': str(session.capability)}
    if decoded != expected:
        raise PermissionDenied('Session capability mismatch')
    if check:
        check_session_authority(session)
    return session


def check_session_authority(session, *, connection=True):
    if not session.user_id:
        raise PermissionDenied('Agent session owner no longer exists')
    if session.date_closed or session.date_expires <= timezone.now():
        raise PermissionDenied('Agent session expired or closed')
    check_agent_organization(session.user, session.org_id)
    if not AgentApplication.objects.filter(
        application=session.application, resource=session.resource, is_active=True,
    ).exists() or not authority_exists(session.user_id, session.application_id, session.oauth_token_id, session.oauth_family):
        raise PermissionDenied('OAuth authorization revoked')
    if connection and not session.connection_token_id:
        raise Conflict('Complete connection credentials in the browser first')
    if connection:
        with tmp_to_org(session.org_id):
            session.connection_token.is_valid(check_expiration=not session.credentials_released)


def check_handoff_authority(session):
    """Authorize a fresh human connection independently of the native transport."""
    from assets.models import Asset
    from authentication.models import ConnectionToken
    from perms.utils import PermAssetDetailUtil

    check_session_authority(session, connection=False)
    with tmp_to_org(session.org_id):
        asset = get_object_or_404(Asset, pk=session.requested['asset_id'], is_active=True)
        protocol = session.requested['protocol']
        if protocol not in SUPPORTED_PROTOCOLS - {'sftp'}:
            raise ValidationError('This operation requires a shell or database session')
        account = PermAssetDetailUtil(session.user, asset).validate_permission(session.requested['account'], protocol)
        if not ConnectionToken.has_account_permission(account, protocol) or account.date_expired <= timezone.now():
            raise PermissionDenied('Asset account or protocol is not authorized')


def same_principal(context, session):
    if (context['user_id'], context['application_id'], context['org_id']) != (
        str(session.user_id), session.application_id, session.org_id,
    ):
        raise PermissionDenied('Operation belongs to another authorization context')


def session_data(session):
    action = session.actions.filter(kind='connect_asset').first()
    return {
        'id': str(session.id), 'status': session.status, 'action_id': str(action.id) if action else None,
        'connection_token_id': str(session.connection_token_id) if session.connection_token_id else None, 'session_token': session_capability(session),
        'terminal_session_id': str(session.terminal_session_id) if session.terminal_session_id else None,
        'approval_url': f'/core/auth/agent/session/{session.id}/',
        'expires_at': session.date_expires.isoformat(),
        'protocol': session.requested.get('protocol', ''),
        'requires_terminal': session.requested.get('requires_terminal', False),
    }


def create_session(node, data):
    from assets.models import Asset

    require_keys(data, ('context_token', 'asset_id', 'account', 'protocol', 'idempotency_key', 'remote_addr'),
                 ('context_token', 'asset_id', 'account', 'protocol', 'idempotency_key'))
    context, user = context_identity(node, data['context_token'])
    key = text_field(data['idempotency_key'], 'idempotency_key')
    account = text_field(data['account'], 'account')
    protocol = text_field(data['protocol'], 'protocol', 16)
    if protocol not in SUPPORTED_PROTOCOLS:
        raise ValidationError('Protocol does not have an Agent execution adapter')
    requested = {'asset_id': str(identifier(data['asset_id'])), 'account': account, 'protocol': protocol}
    request_hash = fingerprint(requested)
    with tmp_to_org(context['org_id']), transaction.atomic():
        # Serialize a user's creation requests, including the first request for
        # an idempotency key. Unique constraints remain the final DB boundary.
        User.objects.select_for_update().get(pk=user.pk)
        existing = AgentSession.objects.select_for_update().filter(user=user, application_id=context['application_id'], idempotency_key=key).first()
        if existing:
            if existing.request_hash != request_hash or existing.terminal_id != node.id:
                raise Conflict('Connection idempotency key belongs to another request or node')
            check_session_authority(existing, connection=False)
            refresh_connection_status(existing)
            return session_data(existing)
        if AgentSession.objects.filter(user=user, date_closed__isnull=True, date_expires__gt=timezone.now()).count() >= 16:
            raise Conflict('Agent session quota reached')
        asset = get_object_or_404(Asset, pk=requested['asset_id'], is_active=True)
        remote_addr = text_field(data.get('remote_addr', ''), 'remote_addr', 128, empty=True)
        from perms.utils import PermAssetDetailUtil
        permitted = PermAssetDetailUtil(user, asset).validate_permission(account, protocol)
        if not permitted or permitted.date_expired <= timezone.now():
            raise PermissionDenied('Asset account or protocol is not authorized')
        connection_request = {**requested, 'remote_addr': remote_addr, 'requires_credentials': not permitted.has_secret}
        token = None
        # Missing credentials are supplied only by the logged-in owner in
        # Core. Existing managed and cached same-name credentials are reused.
        if permitted.has_secret:
            from common.exceptions import JMSException
            try:
                token = create_connection_token(user, connection_request)
            except JMSException as error:
                if str(error.detail.code) != 'acl_face_online':
                    raise
                # Only the browser can host the required live monitor. Keep
                # the logical session so it can request a fresh human handoff.
                connection_request['requires_terminal'] = True
        session = AgentSession.objects.create(
            user=user, application_id=context['application_id'], terminal=node, connection_token=token, requested=connection_request,
            oauth_token_id=context['token_id'], oauth_family=context['family'] or None, resource=context['resource'],
            org_id=asset.org_id, idempotency_key=key, request_hash=request_hash,
            status='ready' if token and token.acl_ready else 'awaiting_approval',
            date_expires=timezone.now() + timedelta(seconds=SESSION_TTL),
        )
        AgentAction.objects.create(
            session=session, user=user, application_id=session.application_id, org_id=session.org_id,
            kind='connect_asset', idempotency_key='connect:' + str(session.id), request=requested,
            request_hash=request_hash, status='queued' if token and token.acl_ready else 'awaiting_approval',
        )
        return session_data(session)


def refresh_connection_status(session):
    if not session.connection_token_id:
        return
    token = session.connection_token
    if not session.credentials_released and not token.acl_ready:
        from authentication.services.connection_acl import advance_acl
        request = SimpleNamespace(user=session.user, method='GET', data={})
        token = advance_acl(token, request)
        session.connection_token = token
    if token.acl_context.get('cancelled') or token.acl_context.get('error'):
        session.status = 'rejected'
        session.actions.filter(kind='connect_asset', status__in=('accepted', 'queued', 'awaiting_approval')).update(
            status='rejected', date_finished=timezone.now(), result={'error': 'Connection controls rejected or cancelled'},
        )
    elif token.acl_ready:
        token.is_valid(check_expiration=not session.credentials_released)
        session.status = 'ready'
    else:
        session.status = 'awaiting_approval'
    session.save(update_fields=['status'])


def create_connection_token(user, requested, credentials=None, *, face_monitor_token=''):
    from authentication.services.connection_token import ConnectionTokenService
    from authentication.serializers import ConnectionTokenSerializer
    request = SimpleNamespace(
        user=user, data={}, query_params={'acl_stepwise': '1'},
        META={'REMOTE_ADDR': requested.get('remote_addr', '')}, headers={},
    )
    if face_monitor_token:
        request.query_params['face_monitor_token'] = face_monitor_token
    values = {
        'asset': requested['asset_id'], 'account': requested['account'], 'protocol': requested['protocol'],
        'connect_method': 'web_sftp' if requested['protocol'] == 'sftp' else 'web_cli',
    }
    if credentials:
        require_keys(credentials, ('input_username', 'input_secret', 'input_secret_type'))
        # The encrypted serializer field is a transport concern. Validate the
        # remaining fields normally, then supply the browser's TLS-protected
        # secret as an already-decoded value to the existing validation flow.
        values.update({k: v for k, v in credentials.items() if k != 'input_secret'})
    serializer = ConnectionTokenSerializer(data=values, context={'request': request})
    serializer.is_valid(raise_exception=True)
    if credentials and credentials.get('input_secret'):
        serializer.validated_data['input_secret'] = text_field(credentials['input_secret'], 'input_secret', 40960)
    token = ConnectionTokenService.for_request(
        request, verified_remote_addr=requested.get('remote_addr', ''),
    ).create_token(serializer)
    token.date_expired = timezone.now() + timedelta(minutes=15)
    token.save(update_fields=['date_expired'])
    return token


def validate_action_request(kind, request):
    fields = {
        'execute_command': ('command', 'prepared_command', 'cwd', 'env', 'timeout_seconds'),
        'open_terminal': ('timeout_seconds',),
    }.get(kind, ('path', 'destination', 'size', 'sha256', 'limit', 'content', 'overwrite', 'timeout_seconds'))
    require_keys(request, fields)
    if len(canonical(request).encode()) > 65536:
        raise ValidationError('Action request exceeds 64 KiB')
    if kind == 'execute_command':
        text_field(request.get('command'), 'command', 4096)
        if 'prepared_command' in request:
            text_field(request['prepared_command'], 'prepared_command', 65536)
        cwd = request.get('cwd', '')
        text_field(cwd, 'cwd', 4096, empty=True)
        if cwd and not cwd.startswith('/'):
            raise ValidationError('Working directory must be absolute')
        env = request.get('env', {})
        if not isinstance(env, dict) or len(env) > 32:
            raise ValidationError('Invalid environment')
        import re
        for name, value in env.items():
            if not isinstance(name, str) or not re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', name):
                raise ValidationError('Invalid environment variable name')
            text_field(value, 'env', 8192, empty=True)
    elif kind.startswith('file_'):
        text_field(request.get('path'), 'path', 4096)
        if 'destination' in request:
            text_field(request['destination'], 'destination', 4096)
        if 'size' in request:
            integer(request['size'], 'size', 0, 1024 * 1024 * 1024)
    if 'timeout_seconds' in request:
        integer(request['timeout_seconds'], 'timeout_seconds', 1, 600)


def create_action(node, data):
    require_keys(data, ('context_token', 'session_id', 'kind', 'idempotency_key', 'request'),
                 ('context_token', 'session_id', 'kind', 'idempotency_key', 'request'))
    context, user = context_identity(node, data['context_token'])
    kind = text_field(data['kind'], 'kind', 32)
    if kind not in ACTION_KINDS:
        raise ValidationError('Unsupported action kind')
    key = text_field(data['idempotency_key'], 'idempotency_key')
    validate_action_request(kind, data['request'])
    with tmp_to_org(context['org_id']), transaction.atomic():
        User.objects.select_for_update().get(pk=user.pk)
        session = get_object_or_404(AgentSession.objects.select_for_update(), pk=identifier(data['session_id']), terminal=node)
        same_principal(context, session)
        if kind == 'open_terminal':
            check_handoff_authority(session)
        else:
            check_session_authority(session)
        if kind.startswith('file_') and session.connection_token.protocol != 'sftp':
            raise ValidationError('File operations require an SFTP session')
        if kind == 'execute_command' and session.requested['protocol'] != 'ssh' and (data['request'].get('cwd') or data['request'].get('env')):
            raise ValidationError('Working directory and environment apply only to SSH execution')
        if kind == 'execute_command' and session.connection_token.protocol == 'sftp':
            raise ValidationError('This operation requires a shell or database session')
        if kind != 'open_terminal' and (session.status != 'ready' or not session.credentials_released or not session.actions.filter(kind='connect_asset', status='succeeded').exists()):
            raise Conflict('Asset connection is not ready')
        request_hash = fingerprint({'session_id': str(session.id), 'kind': kind, 'request': data['request']})
        existing = AgentAction.objects.filter(user=user, application_id=session.application_id, idempotency_key=key).first()
        if existing:
            if existing.request_hash != request_hash:
                raise Conflict('Idempotency key was already used for different parameters')
            return action_data(existing)
        if session.actions.exclude(status__in=FINAL_STATES).count() >= 32:
            raise Conflict('Agent action queue is full')
        action = AgentAction.objects.create(
            session=session, user=user, application_id=session.application_id, org_id=session.org_id,
            kind=kind, idempotency_key=key, request=data['request'], request_hash=request_hash,
        )
        return action_data(action)


def command_policy(session, command):
    # Use the same current connection policy and command groups as terminal
    # execution, rather than accepting a client-supplied ACL or approval ID.
    priorities = {'reject': 0, 'review': 1, 'notify_and_warn': 2, 'warning': 3, 'accept': 4}
    rules = sorted(session.connection_token.command_filter_acls, key=lambda a: (a.priority, priorities.get(a.action, 5), str(a.id)))
    for rule in rules:
        for group in rule.command_groups.all():
            matched, _ = group.match(command)
            if matched:
                digest = fingerprint({
                    'acl': str(rule.id), 'action': rule.action, 'priority': rule.priority,
                    'group': str(group.id), 'type': group.type, 'content': group.content, 'ignore_case': group.ignore_case,
                    'reviewers': sorted(str(pk) for pk in rule.reviewers.values_list('pk', flat=True)),
                })
                return rule, group, digest
    return None, None, fingerprint({'action': 'accept'})


def authorize_action(action):
    from perms.const import ActionChoices

    if action.cancel_requested or action.status in FINAL_STATES or action.status in ('dispatching', 'running', 'awaiting_input'):
        return
    session = action.session
    if action.kind == 'open_terminal':
        check_handoff_authority(session)
    else:
        check_session_authority(session)
        if not session.terminal_session_id:
            raise Conflict('A real terminal session must be registered before executing')
    if action.kind.startswith('file_'):
        required = {
            'file_read': ActionChoices.download, 'file_download': ActionChoices.download,
            'file_write': ActionChoices.upload, 'file_upload': ActionChoices.upload,
            'file_mkdir': ActionChoices.upload, 'file_remove': ActionChoices.delete,
            'file_rename': ActionChoices.upload | ActionChoices.delete,
        }.get(action.kind, ActionChoices.connect)
        if not ActionChoices.contains(session.connection_token.actions, required):
            raise PermissionDenied('File operation is not permitted')
    if action.kind == 'execute_command':
        rule, group, policy_hash = command_policy(session, action.request['command'])
        action.result.pop('command_policy', None)
        if rule and rule.action == 'reject':
            action.status = 'rejected'
            action.result = {'error': 'Command rejected by current ACL', 'acl_id': str(rule.id)}
            action.date_finished = timezone.now()
        elif rule and rule.action == 'notify_and_warn':
            action.status, action.date_finished = 'rejected', timezone.now()
            action.result = {
                'error': 'Command requires user confirmation; call open_terminal to continue in the controlled terminal',
                'requires_terminal': True, 'acl_id': str(rule.id),
            }
        elif rule and rule.action == 'review':
            if action.ticket_id and action.policy_hash != policy_hash:
                action.status = 'rejected'
                action.result = {'error': 'Approval policy changed; submit a new operation'}
                action.date_finished = timezone.now()
            elif not action.ticket_id:
                if not rule.reviewers.exists():
                    raise PermissionDenied('Command approval has no reviewer')
                ticket = rule.create_command_review_ticket(
                    action.request['command'], session.terminal_session, rule, action.org_id,
                )
                # A reviewer must see the exact context, not only the shell text.
                ticket.comment = 'Agent action ' + str(action.id) + '\nRequest SHA256: ' + action.request_hash + '\n' + canonical(action.request)
                ticket.meta = {**ticket.meta, 'agent_action': {'id': str(action.id), 'request_hash': action.request_hash}}
                ticket.save(update_fields=['comment', 'meta'])
                action.ticket, action.policy_hash, action.status = ticket, policy_hash, 'awaiting_approval'
            elif (action.ticket.meta.get('agent_action') != {'id': str(action.id), 'request_hash': action.request_hash}
                  or action.ticket.apply_run_command != action.request['command'][:4090]
                  or str(action.ticket.apply_from_session_id) != str(session.terminal_session_id)
                  or str(action.ticket.apply_from_cmd_filter_acl_id) != str(rule.id)):
                action.status, action.date_finished = 'rejected', timezone.now()
                action.result = {'error': 'Approval does not match the immutable action'}
            elif action.ticket.state == 'approved':
                if timezone.now() - action.date_created > timedelta(minutes=15):
                    action.status, action.date_finished = 'expired', timezone.now()
                else:
                    action.status = 'queued'
            elif action.ticket.state in ('rejected', 'closed'):
                action.status, action.date_finished = 'rejected', timezone.now()
            else:
                action.status = 'awaiting_approval'
        else:
            if action.ticket_id and action.policy_hash != policy_hash:
                action.status, action.date_finished = 'rejected', timezone.now()
                action.result = {'error': 'Approval policy changed; submit a new operation'}
            else:
                action.status, action.policy_hash = 'queued', policy_hash
                action.result = {}
                if rule and rule.action == 'warning':
                    from terminal.const import RiskLevelChoices
                    action.result['command_policy'] = {
                        'action': rule.action, 'acl_id': str(rule.id), 'group_id': str(group.id),
                        'risk_level': RiskLevelChoices.warning,
                    }
                    action.command_warning = (rule, group)
    else:
        action.status = 'queued'
    action.save(update_fields=['status', 'ticket', 'policy_hash', 'result', 'date_finished'])
    finish_action_controls(action)


def notify_action_warning(action):
    """Publish once at the successful dispatch claim, using existing recipients."""
    warning = getattr(action, 'command_warning', None)
    if not warning:
        return
    from terminal.notifications import CommandWarningMessage
    rule, group = warning
    terminal = action.session.terminal_session
    command = {
        'input': action.request['command'], 'user': terminal.user, 'asset': terminal.asset,
        'session': str(terminal.id), 'org_id': action.org_id,
        'risk_level': action.result['command_policy']['risk_level'],
        '_cmd_filter_acl': rule, '_cmd_group': group, '_account': terminal.account,
        '_org_name': terminal.org.name, '_protocol': terminal.protocol,
        '_remote_addr': terminal.remote_addr, '_login_from': terminal.get_login_from_display(),
        '_time': timezone.now(),
    }
    for reviewer in rule.reviewers.all():
        message = CommandWarningMessage(reviewer, command)
        transaction.on_commit(message.publish_async)


def action_data(action):
    return {
        'id': str(action.id), 'action_id': str(action.id), 'session_id': str(action.session_id),
        'kind': action.kind, 'status': action.status, 'request_hash': action.request_hash,
        'cancel_requested': action.cancel_requested, 'last_sequence': action.last_sequence,
        'result': action.result, 'handoff_url': f'/core/auth/agent/session/{action.session_id}/?action={action.id}' if action.kind == 'open_terminal' else None,
        'date_created': action.date_created.isoformat(),
        'date_started': action.date_started.isoformat() if action.date_started else None,
        'date_finished': action.date_finished.isoformat() if action.date_finished else None,
        'audit_url': f'/core/auth/agent/audit/actions/{action.id}/?oid={action.org_id}',
        'approval_url': f'/ui/#/tickets/tickets/{action.ticket_id}?type=command_confirm' if action.ticket_id else None,
    }


def cancel_connection_controls(token):
    if token:
        from authentication.services.connection_acl import close_cancelled_review
        token = type(token).objects.select_for_update().get(pk=token.pk)
        token.acl_context = {**token.acl_context, 'cancelled': True}
        token.is_active = False
        token.save(update_fields=['acl_context', 'is_active'])
        if token.from_ticket_id and token.from_ticket.status == 'open':
            transaction.on_commit(lambda: close_cancelled_review(token.from_ticket))


def finish_action_controls(action):
    """Finish pending human controls without changing completed approval history."""
    if action.status not in FINAL_STATES:
        return
    if action.ticket_id and action.ticket.status == 'open':
        from authentication.services.connection_acl import close_pending_review
        if action.ticket.meta.get('agent_action') == {'id': str(action.id), 'request_hash': action.request_hash}:
            transaction.on_commit(lambda: close_pending_review(action.ticket))
    if action.status != 'succeeded':
        if action.kind == 'connect_asset':
            cancel_connection_controls(action.session.connection_token)
        elif action.kind == 'open_terminal':
            cancel_connection_controls(action.interactive_token)


def append_event(action, data):
    require_keys(data, ('session_token', 'event_id', 'action_id', 'occurred_at', 'sequence', 'state', 'payload'),
                 ('session_token', 'event_id', 'sequence', 'state', 'payload'))
    if data.get('action_id') and identifier(data['action_id']) != action.id:
        raise ValidationError('Event action mismatch')
    event_id = identifier(data['event_id'])
    sequence = integer(data['sequence'], 'sequence', 1, 1000000)
    state, payload = text_field(data['state'], 'state', 32), data['payload']
    if state not in FINAL_STATES | {'running', 'dispatching', 'awaiting_approval', 'queued', 'awaiting_input'}:
        raise ValidationError('Invalid execution state')
    if not isinstance(payload, dict):
        raise ValidationError('Invalid event payload')
    if data.get('occurred_at'):
        from django.utils.dateparse import parse_datetime
        occurred = text_field(data['occurred_at'], 'occurred_at', 64)
        if not parse_datetime(occurred):
            raise ValidationError('Invalid event occurrence time')
        if '_executor_occurred_at' in payload:
            raise ValidationError('Reserved event payload field')
        payload = {**payload, '_executor_occurred_at': occurred}
    encoded = canonical(payload).encode()
    if len(encoded) > 128 * 1024:
        raise ValidationError('Event payload exceeds 128 KiB')
    digest = fingerprint({'sequence': sequence, 'state': state, 'payload': payload})
    existing = AgentEvent.objects.filter(event_id=event_id).first()
    if existing:
        if existing.action_id != action.id or existing.payload_hash != digest:
            raise Conflict('Event ID was already used for different evidence')
        return
    if sequence != action.last_sequence + 1:
        raise Conflict('Events must be delivered in sequence')
    already_final = action.status in FINAL_STATES
    # The executor may deliver its final observation after Core has already
    # cancelled/rejected the action or completed a human handoff. Retain that
    # evidence in order without allowing it to replace Core's terminal state.
    # A crash after the executor's intent may leave its claim undelivered.
    # Unknown closes that uncertainty; it never grants permission to execute.
    if not already_final and action.status not in ('dispatching', 'running', 'awaiting_input') and state not in ('rejected', 'failed', 'expired', 'cancelled', 'unknown'):
        raise Conflict('Execution has not been claimed')
    if state == 'awaiting_input' and action.kind != 'open_terminal':
        raise ValidationError('Only a controlled terminal handoff can await user input')
    if action.status == 'running' and state not in FINAL_STATES | {'running'}:
        raise Conflict('Execution state cannot move backwards')
    if action.status == 'dispatching' and state not in FINAL_STATES | {'running', 'dispatching', 'awaiting_input'}:
        raise Conflict('Execution state cannot move backwards')
    if state == 'cancelled' and action.status in ('dispatching', 'running') and payload.get('stop_confirmed') is not True:
        raise ValidationError('Cancellation requires remote stop confirmation; otherwise report unknown')
    if state == 'succeeded' and action.kind == 'execute_command' and action.session.requested.get('protocol') == 'ssh':
        if payload.get('exit_code') != 0 or isinstance(payload.get('exit_code'), bool):
            raise ValidationError('Successful SSH execution requires a confirmed zero exit code')
    evidence_limit = 16 * 1024 * 1024 - (0 if state in FINAL_STATES else 128 * 1024)
    if action.evidence_bytes + len(encoded) > evidence_limit:
        raise Conflict('Action evidence quota exceeded')
    AgentEvent.objects.create(
        event_id=event_id, action=action, sequence=sequence, state=state, payload=payload, payload_hash=digest,
    )
    action.last_sequence = sequence
    if not already_final:
        action.status = state
    action.evidence_bytes += len(encoded)
    if state in FINAL_STATES and not already_final:
        policy = action.result.get('command_policy')
        action.result = {**payload, **({'command_policy': policy} if policy else {})}
        action.date_finished = timezone.now()
    action.save(update_fields=['last_sequence', 'status', 'evidence_bytes', 'result', 'date_finished'])
    finish_action_controls(action)


def audit_queryset(user, model):
    from orgs.utils import get_current_org
    queryset = model.objects.all()
    if get_current_org().is_root() and not user.has_perm('orgs.view_rootorg'):
        from django.db.models import CharField
        from django.db.models.functions import Cast
        org_ids = user.orgs.annotate(agent_org_id=Cast('id', CharField())).values('agent_org_id')
        queryset = queryset.filter(org_id__in=org_ids)
    if not user.has_perm(f'terminal.view_{model.__name__.lower()}'):
        queryset = queryset.filter(user=user)
    return queryset


def record_audit_read(item):
    from audits.handler import create_or_update_operate_log
    from audits.const import ActionChoices
    create_or_update_operate_log(ActionChoices.view, item._meta.verbose_name, force=True, resource=item)
