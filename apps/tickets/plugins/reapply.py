"""Prepare editable requests; never reuse approvals or execution state."""
from django.utils.translation import gettext
from copy import deepcopy

from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from orgs.utils import tmp_to_org, tmp_to_root_org
from tickets.models import Ticket
from tickets.plugins import get_ticket_plugin
from tickets.workflow.approvers import available_users
from .actions import TicketAction


def can_reapply(ticket, user, memberships=None):
    if (not user or not user.is_valid or ticket.applicant_id != user.pk
            or not get_ticket_plugin(ticket.type).self_service):
        return False
    memberships = {} if memberships is None else memberships
    key = (ticket.org_id, user.pk)
    if key not in memberships:
        with tmp_to_org(ticket.org_id):
            memberships[key] = (user.has_perm('tickets.view_ticket')
                                and available_users(ticket.org_id).filter(pk=user.pk).exists())
    return memberships[key]


def source_ticket(source_id, user, ticket_type):
    with tmp_to_root_org():
        ticket = Ticket.objects.filter(pk=source_id, type=ticket_type).first()
    if not ticket or not can_reapply(ticket, user):
        raise PermissionDenied(gettext('Only the applicant can reuse an available manual request.'))
    return ticket


def source_info(ticket):
    return {'id': str(ticket.pk), 'serial_num': ticket.serial_num,
            'org_id': ticket.org_id, 'kind': 'reapply'}


class Reapply(TicketAction):
    method = 'GET'

    def execute(self, ticket, request):
        if not can_reapply(ticket, request.user):
            raise PermissionDenied(gettext('This request cannot be reapplied for by this user.'))
        if ticket.type == 'apply_asset':
            from .apply_asset.reapply import ReapplyAsset
            return ReapplyAsset().execute(ticket, request, kind='reapply')
        plugin = get_ticket_plugin(ticket.type)
        serializer = plugin.get_request_serializer(context={'request': request, 'org_id': ticket.org_id})
        instance = getattr(ticket, 'workflow_instance', None)
        original = instance.context.get('request', ticket.request_data) if instance else ticket.request_data
        data = {name: deepcopy(original[name]) for name, field in serializer.fields.items()
                if name in original and not field.read_only and name != 'files'}
        resources, warnings = {}, []
        for name, field in serializer.fields.items():
            if name not in data or field.style.get('resource') not in ('asset', 'session'):
                continue
            try:
                value = field.run_validation(data[name])
                getattr(serializer, f'validate_{name}')(value)
                if field.style['resource'] == 'asset':
                    from assets.models import Asset
                    obj = Asset.objects.get(pk=value, org_id=ticket.org_id)
                    if not obj.is_active:
                        raise ValidationError(gettext('Inactive asset.'))
                    option = {'id': str(value), 'name': obj.name, 'address': obj.address}
                else:
                    obj = serializer.get_sessions().filter(pk=value, has_replay=True).first()
                    if not obj:
                        raise ValidationError(gettext('Recording unavailable.'))
                    option = {'id': str(value), 'asset': obj.asset, 'account': obj.account,
                              'user': obj.user, 'date_start': obj.date_start.isoformat()}
                resources[name] = [option]
            except ValidationError:
                data.pop(name)
                warnings.append(name)
        if 'accounts' in data:
            names = serializer.account_options(data['asset']) if data.get('asset') else []
            selected = [name for name in data['accounts'] if name in names]
            if selected != data['accounts']:
                warnings.append('accounts')
            data['accounts'] = selected
        return Response({
            'source_ticket': source_info(ticket), 'type': ticket.type,
            'title': ticket.title, 'comment': ticket.comment, 'org_id': ticket.org_id,
            'workflow_id': str(ticket.workflow_id) if ticket.workflow_id else '',
            'request_data': data, 'resources': resources, 'warnings': warnings,
        })
