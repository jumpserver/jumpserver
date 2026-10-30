"""Prepare a new application without changing the source ticket or its grant."""
from django.utils.translation import gettext
from datetime import timedelta
from urllib.parse import urljoin

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from accounts.models import Account
from orgs.utils import tmp_to_org, tmp_to_root_org
from perms.models import AssetPermission
from perms.serializers.permission import ActionChoicesField
from tickets.models import Ticket
from tickets.plugins.actions import TicketAction
from tickets.workflow.approvers import available_users
from tickets.workflow.resources import application_assets, resource_availability


def reapply_kind(ticket, user, memberships=None):
    if ticket.type != 'apply_asset' or not user or not user.is_valid:
        return None
    applicant = ticket.applicant_id == user.pk
    if ticket.state == 'approved' and (
            applicant or any(item.user_id == user.pk for item in ticket.beneficiaries.all())):
        kind = 'renew'
    elif applicant and ticket.state in ('rejected', 'closed', 'expired', 'error', 'pending'):
        kind = 'reapply'
    else:
        return None
    # List serialization shares this request-local cache across rows in the same organization.
    memberships = {} if memberships is None else memberships
    key = (ticket.org_id, user.pk)
    if key not in memberships:
        memberships[key] = available_users(ticket.org_id).filter(pk=user.pk).exists()
    return kind if memberships[key] else None


def source_ticket(source_id, user):
    with tmp_to_root_org():
        ticket = Ticket.objects.filter(pk=source_id, type='apply_asset').first()
    if not ticket or not reapply_kind(ticket, user):
        raise PermissionDenied(gettext('Only the applicant or authorized beneficiary can reuse this request.'))
    return ticket


def source_info(ticket, user):
    return {'id': str(ticket.pk), 'serial_num': ticket.serial_num,
            'org_id': ticket.org_id, 'kind': reapply_kind(ticket, user)}


def validate_reapplication(attrs, request, source_id):
    ticket = source_ticket(source_id, request.user)
    org_id = attrs['org_id']
    with tmp_to_org(org_id):
        assets = application_assets(request, org_id).filter(is_active=True)
        from assets.models import Node
        from tickets.plugins import get_ticket_plugin
        data = attrs['request_data']
        resource_availability(get_ticket_plugin('apply_asset'), request, org_id, data)
        ids = set(data.get('apply_assets', []))
        for node in Node.objects.filter(pk__in=data.get('apply_nodes', []), org_id=org_id):
            ids.update(str(pk) for pk in node.get_all_assets().values_list('pk', flat=True))
        if assets.filter(pk__in=ids).count() != len(ids):
            raise ValidationError({'apply_assets': gettext('Select active assets currently available for application.')})
        names = set(Account.objects.filter(asset_id__in=ids, is_active=True).values_list('username', flat=True))
        if any(name not in names and name not in ('@ALL', '@SPEC', '@USER', '@INPUT', '@ANON')
               for name in data.get('apply_accounts', [])):
            raise ValidationError({'apply_accounts': gettext('Select existing active accounts on the requested assets.')})
        if request.user.pk != ticket.applicant_id and attrs['request_data']['apply_users'] != [str(request.user.pk)]:
            raise PermissionDenied(gettext('A beneficiary can only renew access for themselves.'))
    if parse_datetime(attrs['request_data']['apply_date_expired']) <= timezone.now():
        raise ValidationError({'apply_date_expired': gettext('Select a future expiration time.')})
    attrs['meta'] = {'source_ticket': source_info(ticket, request.user)}
    if ticket.applicant_id == request.user.pk or org_id != ticket.org_id:
        attrs['meta']['source_ticket']['kind'] = 'reapply'


class ReapplyAsset(TicketAction):
    method = 'GET'

    def execute(self, ticket, request, kind=None):
        kind = kind or reapply_kind(ticket, request.user)
        if not kind:
            raise PermissionDenied(gettext('This request cannot be reapplied for by this user.'))
        data = ticket.request_data
        instance = getattr(ticket, 'workflow_instance', None)
        context = instance.context if instance else {}
        approved = context.get('request', {})
        warnings = {}
        permission = AssetPermission.objects.filter(pk=ticket.pk, org_id=ticket.org_id, from_ticket=True).first()
        # Node membership is live; reuse the concrete snapshot, never expand an old node again.
        if 'assets' in context:
            ids = [asset['id'] for asset in context['assets']]
        elif permission:
            ids = [str(pk) for pk in permission.assets.values_list('pk', flat=True)]
            if permission.nodes.exists():
                warnings['nodes'] = True
        else:
            ids = data.get('apply_assets', [])
            if data.get('apply_nodes'):
                warnings['nodes'] = True
        assets = list(application_assets(request, ticket.org_id).filter(pk__in=ids, is_active=True).order_by('name', 'id'))
        valid_ids = {str(asset.pk) for asset in assets}
        if len(valid_ids) != len(set(ids)):
            warnings['assets'] = len(set(ids) - valid_ids)
        selectors = approved.get('account_selectors', data.get('apply_accounts', []))
        names = set(Account.objects.filter(asset__in=assets, is_active=True).values_list('username', flat=True))
        accounts = [name for name in selectors if name in names or name in ('@USER', '@INPUT', '@ANON')]
        removed = set(selectors) - set(accounts) - {'@SPEC'}
        if removed:
            warnings['accounts'] = sorted(removed)
        users = data.get('apply_users') or [str(ticket.applicant_id)]
        if request.user.pk != ticket.applicant_id:
            users = [str(request.user.pk)]
        valid_users = list(available_users(ticket.org_id).filter(pk__in=users).values('id', 'name', 'username'))
        if len(valid_users) != 1 or (users != [str(request.user.pk)] and
                                    'tickets.apply_asset_for_others' not in request.user.get_all_permissions()):
            warnings['beneficiary'] = True
            valid_users = []
        start = timezone.now()
        if kind == 'renew':
            old_expiry = permission.date_expired if permission else parse_datetime(
                approved.get('date_expired') or data.get('apply_date_expired') or '')
            if old_expiry:
                start = max(start, old_expiry)
        duration = timedelta(**{
            'hours' if settings.TICKET_AUTHORIZE_DEFAULT_TIME_UNIT == 'hour' else 'days':
                settings.TICKET_AUTHORIZE_DEFAULT_TIME,
        })
        notice = data.get('apply_expire_soon_notice_minutes')
        if notice and start + duration - timedelta(minutes=notice) <= timezone.now():
            notice = None
        actions = approved.get('actions', data.get('apply_actions', 0))
        return Response({
            'source_ticket': {**source_info(ticket, request.user), 'kind': kind},
            'title': ticket.title, 'comment': ticket.comment, 'org_id': ticket.org_id,
            'workflow_id': str(ticket.workflow_id) if ticket.workflow_id else '',
            'request_data': {
                'apply_users': [str(user['id']) for user in valid_users],
                'apply_assets': [str(asset.pk) for asset in assets], 'apply_nodes': [],
                'apply_accounts': accounts,
                'apply_actions': [action['value'] for action in ActionChoicesField().to_representation(actions)],
                'apply_date_start': start.isoformat(), 'apply_date_expired': (start + duration).isoformat(),
                'apply_expire_soon_notice_minutes': notice,
                **({'resource_description': data['resource_description']} if data.get('resource_description') else {}),
            },
            'warnings': warnings,
            'assets': [{'id': str(asset.pk), 'name': asset.name, 'address': asset.address} for asset in assets],
            'users': valid_users,
        })


def renewal_links(user, permissions):
    ids = [permission.pk for permission in permissions if permission.from_ticket]
    with tmp_to_root_org():
        tickets = Ticket.objects.filter(pk__in=ids, type='apply_asset', state='approved')
        links = []
        for ticket in tickets:
            if reapply_kind(ticket, user) != 'renew':
                continue
            path = (f'/ui/#/tickets/tickets/request-host-perm/create'
                    f'?source_ticket={ticket.pk}&oid={ticket.org_id}')
            links.append({'serial_num': ticket.serial_num, 'title': ticket.title,
                          'url': urljoin(settings.SITE_URL, path)})
    return links
