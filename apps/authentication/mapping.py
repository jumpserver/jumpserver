import uuid

from django.db import transaction

from common.utils import get_logger
from orgs.models import Organization
from orgs.utils import tmp_to_root_org
from rbac.builtin import BuiltinRole
from rbac.const import Scope
from rbac.models import Role, RoleBinding
from users.models import User, UserGroup
from .models import AuthRoleBinding, AuthUserGroupBinding

logger = get_logger(__name__)

MISSING = object()


class AuthMappingError(Exception):
    pass


def normalize_text(value):
    if isinstance(value, bytes):
        value = value.decode('utf-8')
    elif not isinstance(value, str):
        value = str(value)
    return value.strip()


def normalize_values(values):
    if values is None:
        return []
    if not isinstance(values, (list, tuple, set)):
        values = [values]
    normalized = []
    for value in values:
        if value is None:
            continue
        value = normalize_text(value)
        if value:
            normalized.append(value)
    return normalized


def normalize_auth_attributes(attributes, dn=MISSING, groups=MISSING):
    if attributes is MISSING:
        return MISSING
    normalized = {}
    for key, values in (attributes or {}).items():
        key = normalize_text(key).casefold()
        normalized.setdefault(key, []).extend(normalize_values(values))
    if dn is not MISSING:
        normalized['dn'] = normalize_values(dn)
    if groups is not MISSING:
        normalized['groups'] = normalize_values(groups)
    return normalized


def _validate_wildcard(rules):
    wildcard_count = sum(
        normalize_text(rule.get('value', '')) == '*' for rule in rules
    )
    if wildcard_count > 1:
        raise ValueError('Only one wildcard mapping is allowed')


def match_group_mapping(rules, groups=MISSING):
    rules = rules or []
    if not rules:
        return []
    _validate_wildcard(rules)
    has_exact_rules = any(
        normalize_text(rule.get('value', '')) != '*' for rule in rules
    )
    if groups is MISSING and has_exact_rules:
        return None
    if groups is MISSING:
        groups = []
    source_values = {value.casefold() for value in normalize_values(groups)}
    targets = []
    exact_matched = False
    wildcard = None
    for rule in rules:
        value = normalize_text(rule['value'])
        target = normalize_text(rule['user_group_id'])
        if value == '*':
            wildcard = target
            continue
        if value.casefold() not in source_values:
            continue
        exact_matched = True
        if target not in targets:
            targets.append(target)
    if not exact_matched and wildcard and wildcard not in targets:
        targets.append(wildcard)
    return targets


def match_role_mapping(rules, attributes=MISSING):
    rules = rules or []
    if not rules:
        return []
    _validate_wildcard(rules)
    has_exact_rules = any(
        normalize_text(rule.get('value', '')) != '*' for rule in rules
    )
    if attributes is MISSING and has_exact_rules:
        return None
    if attributes is MISSING:
        attributes = {}
    attributes = normalize_auth_attributes(attributes)
    targets = []
    target_keys = set()
    exact_matched = False
    wildcard = None
    for rule in rules:
        attribute = normalize_text(rule.get('attribute', ''))
        value = normalize_text(rule['value'])
        target = {
            'scope': normalize_text(rule['scope']),
            'role_id': normalize_text(rule['role_id']),
            'org_id': None if rule.get('org_id') is None else normalize_text(rule['org_id']),
        }
        if value == '*':
            if attribute:
                raise ValueError('Wildcard role mapping cannot specify an attribute')
            wildcard = target
            continue
        if not attribute:
            raise ValueError('Role mapping attribute is required')
        values = {
            item.casefold()
            for item in attributes.get(attribute.casefold(), [])
        }
        if value.casefold() not in values:
            continue
        exact_matched = True
        key = (target['scope'], target['role_id'], target['org_id'])
        if key not in target_keys:
            target_keys.add(key)
            targets.append(target)
    if not exact_matched and wildcard:
        key = (wildcard['scope'], wildcard['role_id'], wildcard['org_id'])
        if key not in target_keys:
            targets.append(wildcard)
    return targets


class AuthMappingService:
    def __init__(self, source, group_rules=None, role_rules=None):
        self.source = str(source)
        self.group_rules = group_rules or []
        self.role_rules = role_rules or []

    def match(self, attributes=MISSING, groups=MISSING):
        return (
            match_group_mapping(self.group_rules, groups),
            match_role_mapping(self.role_rules, attributes),
        )

    def get_availability_error(self, desired_group_ids, desired_roles):
        if desired_group_ids is None and self.group_rules:
            return 'Authentication group attributes are unavailable'
        if desired_roles is None and self.role_rules:
            return 'Authentication role attributes are unavailable'
        return ''

    @staticmethod
    def validate_target_ids(desired_group_ids, desired_roles):
        values = list(desired_group_ids or [])
        for target in desired_roles or []:
            values.append(target['role_id'])
            if target['org_id'] is not None:
                values.append(target['org_id'])
        for value in values:
            try:
                uuid.UUID(str(value))
            except (AttributeError, TypeError, ValueError) as error:
                message = f'Invalid authentication mapping target ID: {value}'
                raise ValueError(message) from error

    def preview_many(self, records):
        matches = []
        group_ids = set()
        role_ids = set()
        org_ids = set()
        for attributes, groups in records:
            try:
                desired_group_ids, desired_roles = self.match(attributes, groups)
                error = self.get_availability_error(
                    desired_group_ids, desired_roles
                )
                if not error:
                    self.validate_target_ids(desired_group_ids, desired_roles)
            except Exception as exc:
                desired_group_ids, desired_roles = None, None
                error = str(exc)
            matches.append((desired_group_ids, desired_roles, error))
            if error:
                continue
            if desired_group_ids is not None:
                group_ids.update(desired_group_ids)
            if desired_roles is not None:
                role_ids.update(target['role_id'] for target in desired_roles)
                org_ids.update(
                    target['org_id'] for target in desired_roles
                    if target['org_id'] is not None
                )

        try:
            with tmp_to_root_org():
                groups = list(UserGroup.objects.filter(id__in=group_ids))
                group_map = {str(group.id): group for group in groups}
                group_org_ids = {
                    str(group.org_id) for group in groups
                    if str(group.org_id) not in (
                        Organization.ROOT_ID, Organization.SYSTEM_ID,
                    )
                }
                org_ids.update(group_org_ids)
                if group_org_ids:
                    role_ids.add(BuiltinRole.org_user.id)
                role_map = {
                    str(role.id): role
                    for role in Role.objects.filter(id__in=role_ids)
                }
                org_map = {
                    str(org.id): org
                    for org in Organization.objects.filter(id__in=org_ids)
                }
                org_user_role = role_map.get(BuiltinRole.org_user.id)
        except Exception as exc:
            return [
                {
                    'groups': [], 'roles': [],
                    'error': error or str(exc),
                }
                for _, _, error in matches
            ]

        previews = []
        for desired_group_ids, desired_roles, error in matches:
            if error:
                previews.append({
                    'groups': [], 'roles': [], 'error': error,
                })
                continue
            try:
                if desired_group_ids is None:
                    groups = []
                else:
                    groups = self._resolve_groups(
                        desired_group_ids, group_map=group_map
                    )
                groups, group_roles = self._resolve_group_org_roles(
                    groups, org_map=org_map, org_user_role=org_user_role
                )
                if desired_roles is None:
                    roles = []
                else:
                    roles = self._resolve_roles(
                        desired_roles, role_map=role_map, org_map=org_map
                    )
                previews.append({
                    'groups': groups,
                    'roles': self._merge_roles(roles, group_roles),
                    'error': '',
                })
            except Exception as exc:
                previews.append({
                    'groups': [], 'roles': [], 'error': str(exc),
                })
        return previews

    def sync(
            self, user, attributes=MISSING, groups=MISSING,
            raise_errors=False,
    ):
        try:
            desired_group_ids, desired_roles = self.match(attributes, groups)
            availability_error = self.get_availability_error(
                desired_group_ids, desired_roles
            )
            if raise_errors and availability_error:
                raise ValueError(availability_error)
            if desired_group_ids is None and desired_roles is None:
                return False
            with tmp_to_root_org():
                with transaction.atomic():
                    user = User.objects.select_for_update().get(pk=user.pk)
                    changed = False
                    if desired_group_ids is None:
                        groups = self._current_groups(user)
                    else:
                        groups = self._resolve_groups(desired_group_ids)
                    groups, group_roles = self._resolve_group_org_roles(groups)

                    if desired_roles is not None:
                        roles = self._resolve_roles(desired_roles)
                        roles = self._merge_roles(roles, group_roles)
                        changed |= self._sync_roles(user, roles)
                    if desired_group_ids is not None:
                        if desired_roles is None and group_roles:
                            logger.warning(
                                'Skip authentication group sync for %s because '
                                'role attributes are unavailable',
                                user,
                            )
                            return False
                        changed |= self._sync_groups(user, groups)
                    if changed:
                        user.expire_rbac_perms_cache()
                    return changed
        except Exception as error:
            if raise_errors:
                raise AuthMappingError(str(error)) from error
            logger.exception(
                'Failed to sync authentication mappings for %s from %s: %s',
                user, self.source, error,
            )
            return False

    @staticmethod
    def _resolve_groups(group_ids, group_map=None):
        if group_map is None:
            groups = list(UserGroup.objects.filter(id__in=group_ids))
            group_map = {str(group.id): group for group in groups}
        missing = [group_id for group_id in group_ids if group_id not in group_map]
        if missing:
            logger.warning('Skip dangling authentication user groups: %s', missing)
        return [group_map[group_id] for group_id in group_ids if group_id in group_map]

    def _current_groups(self, user):
        return [
            binding.user_group for binding in
            AuthUserGroupBinding.objects.filter(
                source=self.source, user=user,
            ).select_related('user_group')
        ]

    @staticmethod
    def _resolve_group_org_roles(
            groups, org_map=None, org_user_role=None,
    ):
        if org_map is None:
            org_ids = {str(group.org_id) for group in groups}
            orgs = list(Organization.objects.filter(id__in=org_ids))
            org_map = {str(org.id): org for org in orgs}
        valid_groups = []
        desired_roles = []
        role = org_user_role
        seen_org_ids = set()
        for group in groups:
            org_id = str(group.org_id)
            if org_id == Organization.SYSTEM_ID:
                logger.warning('Skip user group in the system organization: %s', group.id)
                continue
            if org_id == Organization.ROOT_ID:
                valid_groups.append(group)
                continue
            org = org_map.get(org_id)
            if not org:
                logger.warning(
                    'Skip user group %s with dangling organization %s',
                    group.id, org_id,
                )
                continue
            if org_id not in seen_org_ids:
                role = role or BuiltinRole.org_user.get_role()
                desired_roles.append((role, org))
                seen_org_ids.add(org_id)
            valid_groups.append(group)
        return valid_groups, desired_roles

    @staticmethod
    def _merge_roles(*role_lists):
        merged = []
        seen = set()
        for roles in role_lists:
            for role, org in roles:
                key = (str(role.id), None if org is None else str(org.id))
                if key in seen:
                    continue
                seen.add(key)
                merged.append((role, org))
        return merged

    @staticmethod
    def _resolve_roles(targets, role_map=None, org_map=None):
        if role_map is None:
            role_ids = {target['role_id'] for target in targets}
            role_map = {
                str(role.id): role
                for role in Role.objects.filter(id__in=role_ids)
            }
        if org_map is None:
            org_ids = {
                target['org_id'] for target in targets
                if target['org_id'] is not None
            }
            org_map = {
                str(org.id): org
                for org in Organization.objects.filter(id__in=org_ids)
            }
        resolved = []
        for target in targets:
            role = role_map.get(target['role_id'])
            org = org_map.get(target['org_id']) if target['org_id'] else None
            invalid = (
                role is None or role.scope != target['scope'] or
                target['role_id'] == BuiltinRole.system_component.id or
                (target['scope'] == Scope.system and target['org_id'] is not None) or
                (target['scope'] == Scope.org and org is None) or
                target['org_id'] == Organization.SYSTEM_ID
            )
            if invalid:
                logger.warning('Skip dangling authentication role target: %s', target)
                continue
            resolved.append((role, org))
        return resolved

    def _sync_groups(self, user, desired_groups):
        current = list(
            AuthUserGroupBinding.objects.select_for_update()
            .filter(source=self.source, user=user)
            .select_related('user_group')
        )
        desired_ids = {str(group.id) for group in desired_groups}
        changed = False
        for binding in current:
            if str(binding.user_group_id) not in desired_ids:
                self._remove_group_binding(user, binding)
                changed = True

        current_ids = {str(binding.user_group_id) for binding in current}
        for group in desired_groups:
            base_exists = user.groups.filter(id=group.id).exists()
            if not base_exists:
                user.groups.add(group)
            if str(group.id) in current_ids:
                if not base_exists:
                    binding = next(
                        item for item in current if item.user_group_id == group.id
                    )
                    other_owned = AuthUserGroupBinding.objects.filter(
                        user=user, user_group=group, owned=True
                    ).exclude(pk=binding.pk).exists()
                    if not other_owned and not binding.owned:
                        binding.owned = True
                        binding.save(update_fields=['owned'])
                changed |= not base_exists
                continue
            other_owned = AuthUserGroupBinding.objects.filter(
                user=user, user_group=group, owned=True
            ).exists()
            AuthUserGroupBinding.objects.create(
                source=self.source,
                user=user,
                user_group=group,
                owned=not base_exists and not other_owned,
            )
            changed = True
        return changed

    def _remove_group_binding(self, user, binding):
        if not binding.owned:
            binding.delete()
            return
        other = (
            AuthUserGroupBinding.objects.select_for_update()
            .filter(user=user, user_group_id=binding.user_group_id)
            .exclude(pk=binding.pk)
            .order_by('-owned', 'date_created')
            .first()
        )
        if other:
            if not user.groups.filter(id=binding.user_group_id).exists():
                user.groups.add(binding.user_group)
            if not other.owned:
                other.owned = True
                other.save(update_fields=['owned'])
            binding.delete()
            return
        user.groups.remove(binding.user_group)
        binding.delete()

    def _sync_roles(self, user, desired_roles):
        current = list(
            AuthRoleBinding.objects.select_for_update()
            .filter(source=self.source, role_binding__user=user)
            .select_related('role_binding')
        )
        desired_bindings = []
        changed = False
        for role, org in desired_roles:
            query = {
                'user': user,
                'role': role,
                'scope': role.scope,
                'org': org,
            }
            role_binding = RoleBinding.objects_raw.filter(**query).first()
            base_exists = role_binding is not None
            if not role_binding:
                role_binding = RoleBinding.objects_raw.create(**query)
            desired_bindings.append(role_binding)
            _, created = AuthRoleBinding.objects.get_or_create(
                source=self.source,
                role_binding=role_binding,
                defaults={'owned': not base_exists},
            )
            changed |= created or not base_exists

        desired_ids = {binding.id for binding in desired_bindings}
        for binding in current:
            if binding.role_binding_id not in desired_ids:
                self._remove_role_binding(user, binding)
                changed = True
        return changed

    @staticmethod
    def _remove_role_binding(user, binding):
        if not binding.owned:
            binding.delete()
            return
        role_binding = binding.role_binding
        other = (
            AuthRoleBinding.objects.select_for_update()
            .filter(role_binding=role_binding)
            .exclude(pk=binding.pk)
            .order_by('-owned', 'date_created')
            .first()
        )
        if other:
            if not other.owned:
                other.owned = True
                other.save(update_fields=['owned'])
            binding.delete()
            return

        if role_binding.scope == Scope.system:
            has_other_system_role = (
                RoleBinding.objects_raw
                .filter(user=user, scope=Scope.system)
                .exclude(pk=role_binding.pk)
                .exists()
            )
            if not has_other_system_role:
                if str(role_binding.role_id) == BuiltinRole.system_user.id:
                    binding.delete()
                    return
                system_user = BuiltinRole.system_user.get_role()
                RoleBinding.objects_raw.get_or_create(
                    user=user,
                    role=system_user,
                    scope=Scope.system,
                    org=None,
                )
        role_binding.delete()
