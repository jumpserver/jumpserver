from django.utils.translation import gettext_lazy as _

from ..base import TicketPlugin


class Plugin(TicketPlugin):
    type = 'apply_asset'
    label = _('Apply for asset')
    self_service = True
    execution_mode = 'automatic'
    apply_serializer = 'tickets.serializers.ticket.apply_asset.ApplyAssetSerializer'

    def build_context(self, ticket):
        from .handler import build_context
        return build_context(ticket)

    def on_approved(self, instance, ticket):
        from .handler import on_approved
        return on_approved(instance, ticket)

    def request_items(self, ticket):
        from assets.models import Asset, Node
        from perms.const import ActionChoices
        data = ticket.request_data
        instance = getattr(ticket, 'workflow_instance', None)
        if instance:
            context = instance.context
            requested = context.get('request', {})
            users = [user['name'] or user['username'] for user in requested.get('users', [])]
            assets = [f"{asset['name']} ({asset['address']})" for asset in context.get('assets', [])]
            nodes = [node['name'] for node in context.get('nodes', [])]
            accounts = requested.get('account_selectors', [])
            actions = requested.get('actions') or 0
            date_start = requested.get('date_start')
            date_expired = requested.get('date_expired')
            notice = requested.get('expire_soon_notice_minutes')
        else:
            asset_ids = data.get('apply_assets') or []
            node_ids = data.get('apply_nodes') or []
            asset_names = {str(asset.pk): f'{asset.name} ({asset.address})' for asset in Asset.objects.filter(
                pk__in=asset_ids, org_id=ticket.org_id,
            )}
            node_names = {str(node.pk): node.value for node in Node.objects.filter(
                pk__in=node_ids, org_id=ticket.org_id,
            )}
            users = data.get('apply_users', [])
            assets = [asset_names.get(pk, pk) for pk in asset_ids]
            nodes = [node_names.get(pk, pk) for pk in node_ids]
            accounts = data.get('apply_accounts') or []
            actions = data.get('apply_actions') or 0
            date_start = data.get('apply_date_start')
            date_expired = data.get('apply_date_expired')
            notice = data.get('apply_expire_soon_notice_minutes')
        return [
            {'name': 'apply_users', 'label': str(_('Authorized users')),
             'value': users},
            {'name': 'apply_nodes', 'label': str(_('Node')),
             'value': nodes},
            {'name': 'apply_assets', 'label': str(_('Asset')),
             'value': assets},
            {'name': 'apply_accounts', 'label': str(_('Accounts')),
             'value': accounts},
            {'name': 'apply_actions', 'label': str(_('Actions')),
             'value': ActionChoices.display(actions)},
            {'name': 'apply_date_start', 'label': str(_('Date start')),
             'value': date_start},
            {'name': 'apply_date_expired', 'label': str(_('Date expired')),
             'value': date_expired},
            {'name': 'apply_expire_soon_notice_minutes', 'label': str(_('Expiration-soon notice minutes')),
             'value': notice},
        ]

    def options(self, request, org_id):
        from django.db.models import Q
        from tickets.workflow.approvers import available_users
        users = available_users(org_id)
        search = request.query_params.get('search', '')[:128]
        if search:
            users = users.filter(Q(name__icontains=search) | Q(username__icontains=search))
        return list(users.order_by('name', 'id').values('id', 'name', 'username')[:100])
