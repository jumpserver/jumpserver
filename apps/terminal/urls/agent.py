from django.urls import path

from terminal.api.agent import AgentAuditAPI, AgentComponentAPI

urlpatterns = [
    path(f'{operation}/', AgentComponentAPI.as_view(operation=operation), name=f'agent-{operation}')
    for operation in ('introspect', 'assets', 'sessions', 'actions')
] + [
    path(f'sessions/<uuid:session_id>/{operation}/', AgentComponentAPI.as_view(operation=operation), name=f'agent-session-{operation}')
    for operation in ('credentials', 'check', 'bind', 'close')
] + [
    path(f'actions/<uuid:action_id>/{operation}/', AgentComponentAPI.as_view(operation=operation), name=f'agent-action-{operation}')
    for operation in ('authorize', 'claim', 'events', 'get', 'cancel')
] + [
    path('audit/sessions/', AgentAuditAPI.as_view(kind='sessions'), name='agent-audit-sessions'),
    path('audit/sessions/<uuid:object_id>/', AgentAuditAPI.as_view(kind='sessions'), name='agent-audit-session'),
    path('audit/actions/', AgentAuditAPI.as_view(kind='actions'), name='agent-audit-actions'),
    path('audit/actions/<uuid:object_id>/', AgentAuditAPI.as_view(kind='actions'), name='agent-audit-action'),
]
