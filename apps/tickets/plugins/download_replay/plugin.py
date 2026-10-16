from django.utils.translation import gettext_lazy as _

from ..base import TicketPlugin


class Plugin(TicketPlugin):
    type = 'download_replay'
    label = _('Download session recording')
    self_service = True
    execution_mode = 'automatic'
    request_serializer = 'tickets.plugins.download_replay.serializer.RequestSerializer'

    @staticmethod
    def _replay_parameters(instance):
        from datetime import timedelta
        from uuid import UUID

        context = instance.context
        if not isinstance(context, dict) or not instance.date_finished:
            return None
        request = context.get('request')
        duration = context.get('duration')
        if not isinstance(request, dict) or type(duration) is not int or not 60 <= duration <= 86400:
            return None
        try:
            session_id = UUID(str(request.get('session')))
        except ValueError:
            return None
        return session_id, instance.date_finished + timedelta(seconds=duration)

    def on_approved(self, instance, ticket):
        from orgs.utils import tmp_to_org
        from terminal.models import Session
        from tickets.workflow.errors import WorkflowConfigurationError

        parameters = self._replay_parameters(instance)
        if (not parameters or ticket.type != self.type or instance.ticket_id != ticket.pk or
                str(instance.org_id) != str(ticket.org_id) or instance.applicant_id != ticket.applicant_id or
                instance.state != 'approved'):
            raise WorkflowConfigurationError('The session recording approval is not valid.')
        session_id, expires_at = parameters
        with tmp_to_org(ticket.org_id):
            if not Session.objects.filter(pk=session_id, org_id=ticket.org_id, has_replay=True).exists():
                raise WorkflowConfigurationError('The requested session recording is no longer available.')
        return {'action': 'grant_replay_download', 'session_id': str(session_id),
                'expires_at': expires_at.isoformat()}

    def get_available_actions(self, ticket, user):
        return self.get_replay_access(ticket, user)[0]

    def get_replay_access(self, ticket, user):
        from django.utils import timezone
        from orgs.utils import current_org, tmp_to_org
        from terminal.models import Session
        from tickets.workflow.approvers import available_users

        if ticket.type != self.type:
            return [], {'state': 'unavailable'}
        if not user or not user.is_authenticated or user.pk != ticket.applicant_id:
            return [], {'state': 'not_applicant'}
        if not current_org.is_root() and str(current_org.id) != str(ticket.org_id):
            return [], {'state': 'unavailable'}
        instance = getattr(ticket, 'workflow_instance', None)
        if not instance:
            return [], {'state': 'unavailable'}
        if (instance.ticket_id != ticket.pk or str(instance.org_id) != str(ticket.org_id) or
                instance.applicant_id != ticket.applicant_id):
            return [], {'state': 'unavailable'}
        if ticket.state == 'pending':
            return [], {'state': 'pending'}
        if ticket.state != 'approved' or ticket.status != 'closed' or instance.state != 'approved':
            return [], {'state': 'unapproved'}
        if not available_users(ticket.org_id).filter(pk=user.pk).exists():
            return [], {'state': 'unavailable'}
        parameters = self._replay_parameters(instance)
        if not parameters:
            return [], {'state': 'unavailable'}
        session_id, expires_at = parameters
        now = timezone.now()
        if instance.date_finished > now:
            return [], {'state': 'unavailable'}
        with tmp_to_org(ticket.org_id):
            if not Session.objects.filter(pk=session_id, org_id=ticket.org_id, has_replay=True).exists():
                return [], {'state': 'unavailable'}
        if expires_at <= now:
            return [], {'state': 'expired', 'expires_at': expires_at.isoformat()}
        actions = [{'type': self.type, 'session_id': str(session_id), 'expires_at': expires_at.isoformat()}]
        return actions, {'state': 'available', 'expires_at': expires_at.isoformat()}

    def options(self, request, org_id):
        from uuid import UUID
        from django.db.models import Q
        from jumpserver.rewriting.pagination import MaxLimitOffsetPagination

        serializer = self.get_request_serializer(context={'request': request, 'org_id': org_id})
        sessions = serializer.get_sessions().filter(has_replay=True)
        search = request.query_params.get('search', '')[:128].strip()
        if search:
            query = (Q(asset__icontains=search) | Q(account__icontains=search) |
                     Q(user__icontains=search) | Q(protocol__icontains=search))
            try:
                query |= Q(pk=UUID(search))
            except ValueError:
                pass
            sessions = sessions.filter(query)
        sessions = sessions.order_by('-date_start', '-id').values(
            'id', 'asset', 'account', 'user', 'protocol', 'date_start', 'is_finished',
        )
        paginator = MaxLimitOffsetPagination()
        paginator.default_limit = 20
        paginator.max_limit = 100
        page = paginator.paginate_queryset(sessions, request)
        return paginator.get_paginated_response(page).data

    def build_context(self, ticket):
        from terminal.models import Session
        from assets.models import Asset
        from tickets.workflow.context import snapshot_assets
        from tickets.workflow.errors import WorkflowConfigurationError
        session = Session.objects.filter(pk=ticket.request_data['session'], org_id=ticket.org_id).first()
        if not session:
            raise WorkflowConfigurationError('The requested session no longer exists.')
        assets = Asset.objects.filter(pk=session.asset_id, org_id=ticket.org_id) if session.asset_id else []
        return {'request': {**ticket.request_data, 'session_asset': session.asset, 'session_user': session.user,
                            'session_account': session.account, 'session_date_start': session.date_start.isoformat()},
                'assets': snapshot_assets(assets, ticket.org_id), 'accounts': [{'username': session.account}],
                'actions': ['download_replay'], 'duration': ticket.request_data['duration']}

    def request_items(self, ticket):
        instance = getattr(ticket, 'workflow_instance', None)
        context = instance.context if instance else {}
        request = context.get('request') if isinstance(context, dict) else None
        if not isinstance(request, dict):
            return []
        fields = [('session_asset', _('Asset')), ('session_account', _('Account')),
                  ('session_user', _('User')), ('session_date_start', _('Date start'))]
        details = [{'name': name, 'label': str(label), 'value': str(request[name])}
                   for name, label in fields if request.get(name) not in (None, '')]
        items = super().request_items(ticket)
        return details + [item for item in items if item['name'] != 'session']
