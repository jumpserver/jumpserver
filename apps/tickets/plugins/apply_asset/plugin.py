from django.utils.translation import gettext_lazy as _

from ..base import TicketPlugin
from .policy import supports_delegated_request


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

    def get_result_resources(self, instance, event, user):
        from orgs.utils import tmp_to_org
        from perms.models import AssetPermission
        from .handler import permission_resource

        resources = super().get_result_resources(instance, event, user)
        with tmp_to_org(instance.org_id):
            permissions = AssetPermission.objects.filter(org_id=instance.org_id)
            # Older action events only recorded the ticket ID. Resolve the
            # existing grant without replaying the handler or rewriting history.
            if 'resources' not in event.data:
                permission = permissions.filter(pk=instance.ticket_id, from_ticket=True).first()
                resources = [permission_resource(permission)] if permission else []
            # User.perms is cached on the user object and may belong to the
            # organization used to read the timeline (for example root).
            can_view = (user is not None and user.is_active and
                        'perms.view_assetpermission' in user.get_all_permissions())
            ids = [resource['id'] for resource in resources if resource.get('type') == 'asset_permission']
            existing = set(str(pk) for pk in permissions.filter(pk__in=ids).values_list('pk', flat=True)) if can_view else set()
        for resource in resources:
            if resource.get('type') != 'asset_permission':
                continue
            resource['label'] = str(_('Asset permission'))
            if resource['id'] in existing:
                resource['url'] = (
                    f"/ui/#/console/perms/asset-permissions/{resource['id']}?oid={instance.org_id}"
                )
        return resources

    def validate_submission(self, ticket, context):
        from tickets.workflow.errors import WorkflowConfigurationError
        if context['request'].get('is_on_behalf') and not supports_delegated_request(ticket.workflow.active_version):
            raise WorkflowConfigurationError(
                'Requests for another user require organization administrator approval on every path.'
            )

    def filter_workflow_options(self, request, org_id, workflows):
        from rest_framework.exceptions import PermissionDenied
        from orgs.utils import tmp_to_org
        beneficiary = request.query_params.get('beneficiary')
        if not beneficiary or beneficiary == str(request.user.pk):
            return workflows
        with tmp_to_org(org_id):
            if not request.user.has_perm('tickets.apply_asset_for_others'):
                raise PermissionDenied()
        return [workflow for workflow in workflows.select_related('active_version')
                if supports_delegated_request(workflow.active_version)]

    def excluded_approver_ids(self, context, applicant_id):
        ids = {str(applicant_id)}
        ids.update(str(user['id']) for user in context.get('request', {}).get('users', [])
                   if isinstance(user, dict) and user.get('id'))
        return ids

    def notify_processed(self, ticket, processor):
        from tickets.utils import send_ticket_processed_mail_to_beneficiaries
        send_ticket_processed_mail_to_beneficiaries(ticket, processor)

    def allow_direct_approval(self, ticket):
        data = ticket.request_data
        return bool((data.get('apply_assets') or data.get('apply_nodes')) and data.get('apply_accounts'))

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
        if not request.user.has_perm('tickets.apply_asset_for_others'):
            users = users.filter(pk=request.user.pk)
        search = request.query_params.get('search', '')[:128]
        if search:
            users = users.filter(Q(name__icontains=search) | Q(username__icontains=search))
        return list(users.order_by('name', 'id').values('id', 'name', 'username')[:100])
