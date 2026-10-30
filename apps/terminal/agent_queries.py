"""Read-only recovery, scoped to the component and current OAuth principal."""
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch
from rest_framework.exceptions import ValidationError

from orgs.utils import tmp_to_root_org
from terminal import agent_service as service
from terminal.models import AgentAction, AgentSession


def scoped_queryset(node, data, model):
    context, user = service.context_identity(node, data['context_token'])
    with tmp_to_root_org():
        queryset = model.objects.filter(
            user=user, application_id=context['application_id'],
            org_id__in=service.authorized_agent_org_ids(user),
            **{'terminal' if model is AgentSession else 'session__terminal': node},
            **{'resource' if model is AgentSession else 'session__resource': context['resource']},
        )
        if model is AgentSession:
            queryset = queryset.prefetch_related(Prefetch(
                'actions', queryset=AgentAction.objects.filter(kind='connect_asset'), to_attr='connect_actions',
            ))
    return queryset


def public_session(session, *, capabilities=False):
    result = {
        'session_id': str(session.id), 'status': session.status,
        'action_id': str(session.connect_actions[0].id) if session.connect_actions else None,
        'asset_id': session.requested.get('asset_id'), 'account': session.requested.get('account'),
        'org_id': session.org_id, 'protocol': session.requested.get('protocol', ''),
        'expires_at': session.date_expires.isoformat(), 'closed': bool(session.date_closed),
        'requires_terminal': session.requested.get('requires_terminal', False),
        'terminal_session_id': str(session.terminal_session_id) if session.terminal_session_id else None,
        'approval_url': f'/core/auth/agent/session/{session.id}/',
        'audit_url': f'/core/auth/agent/audit/sessions/{session.id}/?oid={session.org_id}',
    }
    if capabilities:
        result['capabilities'] = service.session_capabilities(session)
    return result


def public_action(action):
    result = service.action_data(action)
    # Recovery locates IDs; large results and output have their own paged read.
    result.pop('result', None)
    return result


def query(node, operation, data):
    sessions = operation.startswith('sessions/')
    listing = operation.endswith('/list')
    allowed = ('context_token', 'session_id', 'idempotency_key')
    if listing:
        allowed = ('context_token', 'limit', 'offset', 'status')
        if not sessions:
            allowed += ('session_id',)
    service.require_keys(data, allowed, ('context_token',))
    model = AgentSession if sessions else AgentAction
    queryset = scoped_queryset(node, data, model)
    if not sessions and data.get('session_id'):
        queryset = queryset.filter(session_id=service.identifier(data['session_id']))
    if data.get('idempotency_key'):
        queryset = queryset.filter(idempotency_key=service.text_field(data['idempotency_key'], 'idempotency_key'))
    if listing:
        offset = service.integer(data.get('offset', 0), 'offset', 0, 100000)
        limit = service.integer(data.get('limit', 20), 'limit', 1, 100)
        if data.get('status'):
            queryset = queryset.filter(status=service.text_field(data['status'], 'status', 32))
        rows = list(queryset.order_by('-date_created', '-id')[offset:offset + limit + 1])
        serialize = public_session if sessions else public_action
        return {'results': [serialize(row) for row in rows[:limit]],
                'next_offset': offset + limit if len(rows) > limit else None, 'has_more': len(rows) > limit}
    has_id = sessions and bool(data.get('session_id'))
    if has_id == bool(data.get('idempotency_key')):
        raise ValidationError('Provide either an ID or an idempotency key', code='invalid_lookup')
    if has_id:
        instance = get_object_or_404(queryset, pk=service.identifier(data['session_id']))
    else:
        matches = list(queryset[:2])
        if len(matches) > 1:
            raise service.Conflict('Key matches more than one organization; use a resource ID', code='ambiguous_lookup')
        instance = matches[0] if matches else get_object_or_404(queryset.none())
    return public_session(instance, capabilities=True) if sessions else public_action(instance)
