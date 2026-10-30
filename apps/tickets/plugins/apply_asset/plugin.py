from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

from ..base import TicketPlugin
from .policy import supports_delegated_request


class Plugin(TicketPlugin):
    type = 'apply_asset'
    label = _('Apply for asset')
    self_service = True
    custom_form = True
    execution_mode = 'automatic'
    apply_serializer = 'tickets.serializers.ticket.apply_asset.ApplyAssetSerializer'
    resource_serializer = 'tickets.plugins.apply_asset.resources.ResourceSerializer'
    actions = {'reapply_asset': 'tickets.plugins.apply_asset.reapply.ReapplyAsset'}

    def resources_pending(self, data):
        return not ((data.get('apply_assets') or data.get('apply_nodes')) and data.get('apply_accounts'))

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
                gettext('Requests for another user require organization administrator approval on every path.')
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
        # Only the server-side legacy importer preserves the old self-approval policy.
        if 'legacy' in context:
            return set()
        ids = {str(applicant_id)}
        ids.update(str(user['id']) for user in context.get('request', {}).get('users', [])
                   if isinstance(user, dict) and user.get('id'))
        return ids

    def notify_processed(self, ticket, processor):
        from tickets.utils import send_ticket_processed_mail_to_beneficiaries
        send_ticket_processed_mail_to_beneficiaries(ticket, processor)

    def allow_direct_approval(self, ticket):
        data = ticket.request_data
        return super().allow_direct_approval(ticket) and bool(
            (data.get('apply_assets') or data.get('apply_nodes')) and data.get('apply_accounts'))

    def request_items(self, ticket):
        from accounts.const import AliasAccount
        from assets.models import Asset, Node
        from perms.const import ActionChoices
        data = ticket.request_data
        instance = getattr(ticket, 'workflow_instance', None)
        context = instance.context if instance else {}
        requested = context.get('request', {})
        if 'account_selectors' in requested:
            users = [user['name'] or user['username'] for user in requested.get('users', [])]
            assets = [f"{asset['name']} ({asset['address']})" for asset in context.get('assets', [])]
            nodes = [node['name'] for node in context.get('nodes', [])]
            accounts = requested.get('account_selectors', [])
            actions = requested.get('actions') or 0
            date_start = requested.get('date_start')
            date_expired = requested.get('date_expired')
            notice = requested.get('expire_soon_notice_minutes')
        else:
            # Failed legacy context capture must still display the original request.
            relations = context.get('legacy', {}).get('rel_snapshot', ticket.rel_snapshot)
            asset_ids = data.get('apply_assets') or []
            node_ids = data.get('apply_nodes') or []
            asset_names = {str(asset.pk): f'{asset.name} ({asset.address})' for asset in Asset.objects.filter(
                pk__in=asset_ids, org_id=ticket.org_id,
            )}
            node_names = {str(node.pk): node.value for node in Node.objects.filter(
                pk__in=node_ids, org_id=ticket.org_id,
            )}
            applicant = relations.get('applicant') or (str(ticket.applicant) if ticket.applicant else '')
            users = data.get('apply_users', [applicant] if applicant else [])
            assets = relations.get('apply_assets', [asset_names.get(pk, pk) for pk in asset_ids])
            nodes = relations.get('apply_nodes', [node_names.get(pk, pk) for pk in node_ids])
            accounts = data.get('apply_accounts') or []
            actions = data.get('apply_actions') or 0
            date_start = data.get('apply_date_start')
            date_expired = data.get('apply_date_expired')
            notice = data.get('apply_expire_soon_notice_minutes')
        account_labels = dict(AliasAccount.choices)
        return [
            {'name': 'apply_users', 'label': str(_('Authorized users')),
             'value': users},
            {'name': 'apply_nodes', 'label': str(_('Node')),
             'value': nodes},
            {'name': 'apply_assets', 'label': str(_('Asset')),
             'value': assets},
            {'name': 'apply_accounts', 'label': str(_('Accounts')),
             'value': [str(account_labels.get(account, account)) for account in accounts]},
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
