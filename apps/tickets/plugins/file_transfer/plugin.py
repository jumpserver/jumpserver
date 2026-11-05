from datetime import timedelta

from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from ..base import TicketPlugin
from .permissions import base_access, is_executable, executable_protocols


class Plugin(TicketPlugin):
    type = 'file_transfer'
    label = _('File upload / download')
    self_service = True
    execution_mode = 'external'
    request_serializer = 'tickets.plugins.file_transfer.serializer.RequestSerializer'
    actions = {
        'execute_transfer': 'tickets.plugins.file_transfer.actions.ExecuteTransfer',
        'download_transfer_file': 'tickets.plugins.file_transfer.actions.DownloadTransferFile',
        'review_transfer_file': 'tickets.plugins.file_transfer.actions.ReviewTransferFile',
    }

    def get_execution_mode(self, ticket):
        instance = getattr(ticket, 'workflow_instance', None)
        if instance and instance.context.get('file_transfer_version') == 2:
            return 'external'
        return 'automatic' if is_executable(instance) else 'approval_only'

    def build_context(self, ticket):
        from assets.models import Asset
        from tickets.workflow.errors import WorkflowConfigurationError
        from ..resources import account_context
        context = account_context(ticket)
        asset = Asset.objects.get(pk=context['request']['asset'], org_id=ticket.org_id)
        access = base_access(ticket.applicant, asset)
        context['accounts'] = [a for a in context['accounts'] if a['id'] in access and
                               a['secret_type'] in ('password', 'ssh_key') and
                               executable_protocols(asset) & set(access[a['id']]['protocols']) and
                               (asset.type != 'windows' or a['secret_type'] == 'password')]
        if {a['username'] for a in context['accounts']} != set(context['request']['accounts']):
            raise WorkflowConfigurationError(_('Existing access to every requested account is required.'))
        if len(context['accounts']) != 1 or not executable_protocols(asset):
            raise WorkflowConfigurationError(_('Select one Linux SSH/SFTP or Windows WinRM account.'))
        from .storage import claim_files
        account = context['accounts'][0]
        protocol = ('winrm' if asset.type == 'windows' else
                    'sftp' if 'sftp' in access[account['id']]['protocols'] else 'ssh')
        context.update(
            file_transfer_version=2, actions=[ticket.request_data['direction']],
            duration=ticket.request_data['duration'],
            transfer_protocol=protocol, transfer_port=asset.protocols.get(name=protocol).port,
            transfer_address=asset.address,
            transfer_files=claim_files(ticket),
        )
        return context

    def on_approved(self, instance, ticket):
        if instance.context.get('file_transfer_version') == 2:
            from .policy import validate_context, expires_at
            from tickets.models import TicketTransferFile
            validate_context(ticket)
            files = TicketTransferFile.objects.filter(ticket=ticket, kind='upload', purged_at__isnull=True,
                                                       expires_at__gt=timezone.now())
            if files.count() != len(instance.context['transfer_files']):
                from tickets.workflow.errors import WorkflowConfigurationError
                raise WorkflowConfigurationError(_('The uploaded files expired. Submit a new request.'))
            files.update(expires_at=expires_at(ticket))
            return None
        from assets.models import Asset
        from perms.const import ActionChoices
        from perms.models import AssetPermission
        from tickets.workflow.errors import WorkflowConfigurationError
        from ..apply_asset.handler import permission_resource

        if not is_executable(instance):
            return None
        context = instance.context
        asset = Asset.objects.filter(pk=context['request']['asset'], org_id=instance.org_id).first()
        access = base_access(ticket.applicant, asset) if asset else {}
        for account in context['accounts']:
            current = access.get(account['id'])
            if (not current or current['username'] != account['username'] or
                    not set(context['transfer_protocols'][account['id']]).issubset(current['protocols'])):
                raise WorkflowConfigurationError(_('The requested account access changed. Submit a new request.'))
        if AssetPermission.objects.filter(pk=ticket.pk).exists():
            return None
        direction = context['request']['direction']
        permission = AssetPermission.objects.create(
            id=ticket.pk, org_id=instance.org_id, from_ticket=True, name=f'Ticket {ticket.pk}',
            accounts=sorted({a['username'] for a in context['accounts']}),
            protocols=sorted({p for protocols in context['transfer_protocols'].values() for p in protocols}),
            actions={'upload': ActionChoices.upload, 'download': ActionChoices.download}[direction],
            date_start=instance.date_finished,
            date_expired=instance.date_finished + timedelta(seconds=context['duration']),
            comment=f'Ticket {ticket.serial_num}: {ticket.title}',
        )
        permission.assets.add(asset)
        permission.users.add(ticket.applicant)
        return {'action': 'grant_file_transfer', 'ticket': str(ticket.pk),
                'resources': [permission_resource(permission)]}

    def get_result_resources(self, instance, event, user):
        from ..apply_asset.plugin import Plugin as AssetPlugin
        return AssetPlugin().get_result_resources(instance, event, user)

    def get_transfer_status(self, ticket):
        from assets.models import Asset
        from perms.models import AssetPermission
        from perms.utils.permission import AssetPermissionUtil
        from orgs.utils import tmp_to_org
        from .permissions import approved_grants, effective_transfer_actions

        instance = getattr(ticket, 'workflow_instance', None)
        if not is_executable(instance):
            return {'state': 'approval_only'}
        context = instance.context
        status = {'state': 'pending', 'direction': context['request']['direction'],
                  'accounts': [a['username'] for a in context['accounts']],
                  'protocols': sorted({p for names in context['transfer_protocols'].values() for p in names})}
        if ticket.state == 'pending':
            return status

        status['state'] = 'unavailable'
        if ticket.state != 'approved' or instance.state != 'approved' or not instance.date_finished:
            return status
        with tmp_to_org(ticket.org_id):
            grant = AssetPermission.objects.filter(pk=ticket.pk, org_id=ticket.org_id, from_ticket=True).first()
            if not grant:
                return status
            expires = min(grant.date_expired, instance.date_finished + timedelta(seconds=context['duration']))
            status.update(starts_at=grant.date_start.isoformat(), expires_at=expires.isoformat())
            if expires <= timezone.now():
                status['state'] = 'expired'
                return status
            asset = Asset.objects.filter(pk=context['request']['asset'], org_id=ticket.org_id).first()
            if not asset or not ticket.applicant_id:
                return status
            permissions = list(AssetPermissionUtil().get_permissions_for_user_asset(ticket.applicant, asset))
            grants = approved_grants(ticket.applicant, asset, ticket.pk)
            actions = effective_transfer_actions(ticket.applicant, asset, permissions, grants)
            usable = [a['username'] for a in context['accounts'] if actions.get(a['id'])]
            if usable:
                status.update(state='available', accounts=sorted(set(usable)))
            return status

    def get_result(self, ticket, user):
        instance = getattr(ticket, 'workflow_instance', None)
        if instance and instance.context.get('file_transfer_version') == 2:
            from .execution import get_result
            return get_result(ticket, user)
        return {**self.get_transfer_status(ticket), 'actions': []}

    def request_items(self, ticket):
        return [item for item in super().request_items(ticket) if item['name'] != 'files' and item['value'] not in ('', [])]
