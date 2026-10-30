from django.utils.translation import gettext
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
        connections = ticket.meta.get('login_asset_connections') or [{
            'asset_id': data.get('apply_login_asset'), 'account': data.get('apply_login_account', ''),
        }]
        ids = {entry['asset_id'] for entry in connections}
        assets = list(Asset.objects.filter(pk__in=ids, org_id=ticket.org_id))
        if not ids or len(assets) != len(ids):
            raise WorkflowConfigurationError(gettext('The requested asset no longer exists.'))
        return {'assets': snapshot_assets(assets, ticket.org_id),
                'accounts': [{'asset_id': entry['asset_id'], 'username': entry['account']} for entry in connections]}

    def on_approved(self, instance, ticket):
        from ..resources import validate_snapshot_assets
        from authentication.services.connection_acl import get_pending_review_assignees
        from acls.models import LoginAssetACL
        validate_snapshot_assets(instance)
        for token in ticket.connection_tokens.select_for_update().order_by('pk'):
            if token.is_expired or token.acl_context.get('cancelled'):
                continue
            if token.acl_context.get('review_acls'):
                get_pending_review_assignees(token)
            token.complete_acl_requirement('review')
        LoginAssetACL.cache_approved_review(ticket, instance)
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
