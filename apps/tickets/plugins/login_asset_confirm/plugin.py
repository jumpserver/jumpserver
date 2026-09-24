from django.utils.translation import gettext_lazy as _

from ..base import TicketPlugin


class Plugin(TicketPlugin):
    type = 'login_asset_confirm'
    label = _('Login asset confirm')
    execution_mode = 'automatic'

    def build_context(self, ticket):
        from tickets.workflow.context import snapshot_assets
        from tickets.workflow.errors import WorkflowConfigurationError
        from assets.models import Asset
        data = ticket.request_data
        asset_id = data.get('apply_login_asset')
        if not asset_id:
            raise WorkflowConfigurationError('The requested asset no longer exists.')
        asset = Asset.objects.filter(pk=asset_id, org_id=ticket.org_id).first()
        if not asset:
            raise WorkflowConfigurationError('The requested asset no longer exists.')
        return {'assets': snapshot_assets([asset], ticket.org_id),
                'accounts': [{'username': data.get('apply_login_account', '')}]}

    def on_approved(self, instance, ticket):
        from ..resources import validate_snapshot_assets
        validate_snapshot_assets(instance)
        token = getattr(ticket, 'connection_token', None)
        if token:
            from tickets.workflow.errors import WorkflowConfigurationError
            if token.is_expired:
                raise WorkflowConfigurationError('The connection token has expired. Request a new connection.')
            token.is_active = True
            token.save(update_fields=['is_active'])
        return {'action': self.type, 'ticket': str(ticket.pk)}

    def request_items(self, ticket):
        data = ticket.request_data
        instance = getattr(ticket, 'workflow_instance', None)
        assets = instance.context.get('assets', []) if instance else []
        asset = assets[0] if assets else None
        account = (instance.context.get('accounts') or [{}])[0].get('username') if instance else None
        return [
            {'name': 'apply_login_asset', 'label': str(_('Login asset')),
             'value': asset['name'] if asset else data.get('apply_login_asset')},
            {'name': 'apply_login_account', 'label': str(_('Login account')),
             'value': account if account is not None else data.get('apply_login_account')},
            {'name': 'apply_login_user', 'label': str(_('Login user')),
             'value': ticket.rel_snapshot.get('apply_login_user') or str(ticket.applicant)},
        ]
