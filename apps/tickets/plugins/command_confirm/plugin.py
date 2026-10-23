from django.utils.translation import gettext_lazy as _

from ..base import TicketPlugin


class Plugin(TicketPlugin):
    type = 'command_confirm'
    label = _('Command confirm')
    execution_mode = 'external'

    def build_context(self, ticket):
        from assets.models import Asset
        from tickets.workflow.context import snapshot_assets
        from tickets.workflow.errors import WorkflowConfigurationError
        from terminal.models import Session
        data = ticket.request_data
        session = Session.objects.filter(pk=data.get('apply_from_session')).first() if data.get('apply_from_session') else None
        asset = Asset.objects.filter(pk=session.asset_id, org_id=ticket.org_id).first() if session else None
        if not asset:
            raise WorkflowConfigurationError('The command session asset no longer exists.')
        return {'assets': snapshot_assets([asset], ticket.org_id),
                'accounts': [{'username': data.get('apply_run_account', '')}],
                'request': {'command': data.get('apply_run_command', ''), 'session_id': str(session.pk),
                            'acl_id': data.get('apply_from_cmd_filter_acl')}}

    def on_approved(self, instance, ticket):
        from ..resources import validate_snapshot_assets
        validate_snapshot_assets(instance)

    def request_items(self, ticket):
        data = ticket.request_data
        instance = getattr(ticket, 'workflow_instance', None)
        context = instance.context if instance else {}
        requested = context.get('request', {})
        asset = (context.get('assets') or [None])[0]
        account = (context.get('accounts') or [{}])[0].get('username')
        return [
            {'name': 'apply_run_user', 'label': str(_('Run user')),
             'value': ticket.rel_snapshot.get('apply_run_user') or str(ticket.applicant)},
            {'name': 'apply_run_asset', 'label': str(_('Run asset')),
             'value': asset['name'] if asset else data.get('apply_run_asset')},
            {'name': 'apply_run_account', 'label': str(_('Account')),
             'value': account if account is not None else data.get('apply_run_account')},
            {'name': 'apply_run_command', 'label': str(_('Run command')),
             'value': requested.get('command', data.get('apply_run_command'))},
            {'name': 'apply_from_session', 'label': str(_('Session')),
             'value': requested.get('session_id', data.get('apply_from_session'))},
            {'name': 'apply_from_cmd_filter_acl', 'label': str(_('Command filter acl')),
             'value': ticket.rel_snapshot.get('apply_from_cmd_filter_acl') or data.get('apply_from_cmd_filter_acl')},
        ]
