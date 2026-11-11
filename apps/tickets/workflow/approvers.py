from django.utils.translation import gettext
from uuid import UUID

from django.db.models import Q
from django.utils import timezone

from orgs.models import Organization
from orgs.utils import tmp_to_org
from rbac.builtin import BuiltinRole
from rbac.models import RoleBinding
from users.models import User, UserGroup
from .errors import WorkflowConfigurationError


def user_snapshot(user):
    return {'id': str(user.pk), 'name': user.name, 'username': user.username} if user else {}


def available_users(org_id):
    if org_id == Organization.ROOT_ID:
        users = User.objects.all()
    else:
        org = Organization.objects.get(pk=org_id)
        users = User.get_org_users(org=org)
    return users.filter(is_active=True, is_service_account=False).filter(
        Q(date_expired__isnull=True) | Q(date_expired__gt=timezone.now())
    )


def snapshot_ids(values, asset_name):
    if not isinstance(values, list) or not values:
        raise WorkflowConfigurationError(gettext(
            'Asset "{asset}" has no owner. Set its owner on the asset edit page.'
        ).format(asset=asset_name))
    try:
        return {str(UUID(value)) for value in values}
    except (ValueError, TypeError, AttributeError):
        raise WorkflowConfigurationError(gettext(
            'Asset "{asset}" has invalid owner information. Set its owner on the asset edit page.'
        ).format(asset=asset_name))


def excluded_approver_ids(config, context, applicant_id):
    from tickets.plugins import get_ticket_plugin
    ids = {str(applicant_id)} if config['exclude_applicant'] else set()
    ticket_type = context.get('plugin', {}).get('type') or context.get('request', {}).get('type')
    if ticket_type:
        ids.update(get_ticket_plugin(ticket_type).excluded_approver_ids(context, applicant_id))
    return ids


def resolve_approvers(node_instance, context, org_id, applicant_id):
    config = node_instance.node.config
    spec = config['approvers']
    kind = spec['type']
    users = available_users(org_id)
    explicit_ids = None
    if kind == 'user':
        explicit_ids = set(spec['value'])
    elif kind == 'user_group':
        with tmp_to_org(org_id):
            groups = UserGroup.objects.filter(pk__in=spec['value'], org_id=org_id)
            if groups.count() != len(spec['value']):
                raise WorkflowConfigurationError(gettext('An approver group is missing or belongs to another organization.'))
            users = users.filter(groups__in=groups)
    elif kind in ('role', 'org_admin'):
        roles = spec['value'] if kind == 'role' else [BuiltinRole.org_admin.id]
        bindings = RoleBinding.objects_raw.filter(role_id__in=roles).filter(
            Q(scope='org', org_id=org_id) | Q(scope='system', org__isnull=True)
        )
        users = users.filter(pk__in=bindings.values('user_id'))
    elif kind == 'asset_owner':
        assets = context.get('assets')
        if not isinstance(assets, list) or not assets:
            raise WorkflowConfigurationError(gettext(
                'This request has no assets. Select assets or use another approver source.'
            ))
        explicit_ids = set()
        asset_owners = []
        for asset in assets:
            if not isinstance(asset, dict):
                raise WorkflowConfigurationError(gettext('Invalid asset information in the request.'))
            name = asset.get('name') or asset.get('id') or '-'
            owner_ids = snapshot_ids(asset.get('owner_ids'), name)
            asset_owners.append((name, owner_ids))
            explicit_ids.update(owner_ids)
    else:
        raise WorkflowConfigurationError(gettext('Unknown approver resolver.'))
    if explicit_ids is not None:
        users = users.filter(pk__in=explicit_ids)
        eligible_ids = {str(pk) for pk in users.values_list('pk', flat=True)}
        if eligible_ids != explicit_ids:
            if kind == 'asset_owner':
                names = ', '.join(name for name, ids in asset_owners if ids - eligible_ids)
                raise WorkflowConfigurationError(gettext(
                    'The owners of these assets are unavailable (inactive, expired, deleted, or outside this organization): '
                    '{assets}. Set valid owners on the asset edit page.'
                ).format(assets=names))
            raise WorkflowConfigurationError(gettext('A configured approver is inactive, missing, or outside the organization.'))
    excluded = excluded_approver_ids(config, context, applicant_id)
    candidates = users
    if excluded:
        users = users.exclude(pk__in=excluded)
    result = list(users.distinct().order_by('id')[:1001])
    if not result and excluded and candidates.exists():
        runs = node_instance.instance.node_instances
        started_at = runs.filter(node__type='start').latest('date_created').date_created
        level = runs.filter(node__type='approval', date_created__gte=started_at).count()
        raise WorkflowConfigurationError(gettext(
            'Approval {level} has no eligible approvers after excluding the applicant or authorized users. '
            'Adjust the approvers or select another workflow.'
        ).format(level=level))
    if not result or len(result) > 1000:
        raise WorkflowConfigurationError(gettext('An approval node must resolve between 1 and 1000 eligible approvers.'))
    return result
