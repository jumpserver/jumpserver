"""Owner-only human controls for active Agent sessions."""
import uuid
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.views import View
from rest_framework.exceptions import APIException

from authentication.services.connection_acl import acl_state, advance_acl
from orgs.utils import tmp_to_org, tmp_to_root_org
from terminal import agent_service as service
from terminal.models import AgentSession


class AgentSessionView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.is_valid:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, session_id):
        return self.handle(request, session_id)

    @transaction.atomic
    def post(self, request, session_id):
        return self.handle(request, session_id)

    def handle(self, request, session_id):
        with tmp_to_root_org():
            queryset = AgentSession.objects.filter(user=request.user)
            if request.method == 'POST':
                queryset = queryset.select_for_update()
            session = get_object_or_404(queryset, pk=session_id)
        try:
            service.check_session_authority(session, connection=False)
        except APIException as exc:
            return HttpResponse(str(exc.detail), status=exc.status_code, headers={
                'Cache-Control': 'no-store', 'Referrer-Policy': 'same-origin',
            })
        action_id = request.GET.get('action') or request.POST.get('action')
        error, token, action, terminal_url = '', None, None, None
        with tmp_to_org(session.org_id):
            try:
                if request.method == 'POST' and request.POST.get('operation') == 'revoke':
                    if session.oauth_family:
                        from oauth2_provider.models import get_refresh_token_model
                        get_refresh_token_model().revoke_family(session.oauth_family)
                    elif session.oauth_token_id:
                        session.oauth_token.delete()
                    raise service.Conflict('Agent authorization revoked; active operations are being stopped')
                if action_id:
                    service.check_handoff_authority(session)
                    actions = session.actions.select_for_update() if request.method == 'POST' else session.actions
                    action = get_object_or_404(actions, pk=service.identifier(action_id), kind='open_terminal')
                    if action.status in service.FINAL_STATES or action.cancel_requested:
                        return HttpResponse('This terminal handoff has finished', status=410, headers={
                            'Cache-Control': 'no-store', 'Referrer-Policy': 'same-origin',
                        })
                    token = action.interactive_token
                else:
                    token = session.connection_token
                if request.method == 'POST':
                    if request.POST.get('operation') == 'credentials':
                        if token:
                            raise service.Conflict('Credentials have already been supplied')
                        if action and action.status not in ('dispatching', 'awaiting_input'):
                            raise service.Conflict('The terminal action must be authorized first')
                        credentials = {name: request.POST.get(name, '') for name in (
                            'input_username', 'input_secret', 'input_secret_type',
                        )}
                        credentials['input_secret_type'] = credentials['input_secret_type'] or 'password'
                        token = service.create_connection_token(
                            request.user, session.requested, credentials,
                            face_monitor_token=uuid.uuid4().hex if action else '',
                        )
                        if action:
                            action.interactive_token = token
                            action.save(update_fields=['interactive_token'])
                        else:
                            session.connection_token = token
                            session.save(update_fields=['connection_token'])
                    elif token:
                        payload = {k: v for k, v in request.POST.items() if k not in (
                            'csrfmiddlewaretoken', 'action', 'operation',
                        )}
                        if not payload.get('mfa_code'):
                            payload.pop('mfa_code', None)
                        request.data = payload
                        token = advance_acl(token, request)
                        if payload.get('retry_face') and token.acl_context.get('requirements', {}).get('face') == 'pending':
                            from authentication.services.connection_token import ConnectionTokenService
                            ConnectionTokenService.for_request(request).create_face_verify(str(token.id))
                            token.refresh_from_db()
                    if token and token.acl_ready:
                        token.is_valid()
                        if action:
                            terminal_url = f'/luna/koko/connect?token={token.id}'
                            if not token.face_monitor_token:
                                return HttpResponseRedirect(terminal_url)
                        else:
                            session.status = 'ready'
                            session.save(update_fields=['status'])
                state = acl_state(token) if token else {}
            except APIException as exc:
                error = str(exc.detail)
                state = acl_state(token) if token else {}
            response = render(request, 'terminal/agent_session.html', {
                'session': session, 'action': action, 'token': token, 'state': state, 'error': error,
                'terminal_url': terminal_url,
            })
            response['Cache-Control'] = 'no-store'
            response['Referrer-Policy'] = 'same-origin'
            return response
