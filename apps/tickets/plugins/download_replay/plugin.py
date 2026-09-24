from django.utils.translation import gettext_lazy as _

from ..base import TicketPlugin


class Plugin(TicketPlugin):
    type = 'download_replay'
    label = _('Download session recording')
    self_service = True
    request_serializer = 'tickets.plugins.download_replay.serializer.RequestSerializer'

    def build_context(self, ticket):
        from terminal.models import Session
        from assets.models import Asset
        from tickets.workflow.context import snapshot_assets
        from tickets.workflow.errors import WorkflowConfigurationError
        session = Session.objects.filter(pk=ticket.request_data['session'], org_id=ticket.org_id).first()
        if not session:
            raise WorkflowConfigurationError('The requested session no longer exists.')
        assets = Asset.objects.filter(pk=session.asset_id, org_id=ticket.org_id) if session.asset_id else []
        return {'request': {**ticket.request_data, 'session_asset': session.asset, 'session_user': session.user},
                'assets': snapshot_assets(assets, ticket.org_id), 'accounts': [{'username': session.account}],
                'actions': ['download_replay'], 'duration': ticket.request_data['duration']}
