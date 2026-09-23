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


def snapshot_ids(values):
    if not isinstance(values, list) or not values:
        raise WorkflowConfigurationError('The snapshot does not contain the required approver IDs.')
    try:
        return {str(UUID(value)) for value in values}
    except (ValueError, TypeError, AttributeError):
        raise WorkflowConfigurationError('Invalid approver IDs in the snapshot.')


def resolve_approvers(config, context, org_id, applicant_id):
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
                raise WorkflowConfigurationError('An approver group is missing or belongs to another organization.')
            users = users.filter(groups__in=groups)
    elif kind in ('role', 'org_admin'):
        roles = [BuiltinRole.org_admin.id] if kind == 'org_admin' else spec['value']
        bindings = RoleBinding.objects_raw.filter(role_id__in=roles).filter(
            Q(scope='org', org_id=org_id) | Q(scope='system', org__isnull=True)
        )
        users = users.filter(pk__in=bindings.values('user_id'))
    elif kind == 'applicant_manager':
        applicant = context.get('applicant', {})
        explicit_ids = snapshot_ids([applicant.get('manager_id')] if isinstance(applicant, dict) else [])
    elif kind == 'asset_owner':
        assets = context.get('assets')
        if not isinstance(assets, list) or not assets:
            raise WorkflowConfigurationError('The snapshot does not contain asset owners.')
        explicit_ids = set()
        for asset in assets:
            explicit_ids.update(snapshot_ids(asset.get('owner_ids') if isinstance(asset, dict) else None))
    else:
        raise WorkflowConfigurationError('Unknown approver resolver.')
    if explicit_ids is not None:
        users = users.filter(pk__in=explicit_ids)
        if {str(pk) for pk in users.values_list('pk', flat=True)} != explicit_ids:
            raise WorkflowConfigurationError('A configured approver is inactive, missing, or outside the organization.')
    if config['exclude_applicant']:
        users = users.exclude(pk=applicant_id)
    result = list(users.distinct().order_by('id')[:1001])
    if not result or len(result) > 1000:
        raise WorkflowConfigurationError('An approval node must resolve between 1 and 1000 eligible approvers.')
    return result
