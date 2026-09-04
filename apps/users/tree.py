from collections import defaultdict
from uuid import UUID

from django.db.models import OuterRef, Q, Subquery

from orgs.models import Organization
from orgs.utils import current_org
from users.models import User, UserGroup


__all__ = ['UserGroupTree']


class UserGroupTree:
    """Build the organization -> groups/users tree without N+1 queries."""

    def __init__(self):
        self.org = current_org
        self.org_id = str(self.org.id)
        self.groups = UserGroup.objects.order_by().only('id', 'name', 'org_id')
        self.users = User.get_org_users(self.org).order_by().only(
            'id', 'name', 'username'
        )
        self.group_org_names = {}

    @staticmethod
    def _node_meta(resource_type, resource_id, **data):
        resource_id = str(resource_id)
        return {
            'type': resource_type,
            'data': {
                'id': resource_id,
                'resource_id': resource_id,
                **data,
            },
        }

    def _organization_node(self, has_children):
        name = str(self.org.name)
        return {
            'id': self.org_id,
            'pId': '',
            'name': name,
            'username': '',
            'hasChildren': has_children,
            'isParent': has_children,
            '_isLeaf': not has_children,
            'meta': self._node_meta(
                'organization', self.org_id, name=name
            ),
        }

    def _group_node(self, group, has_children):
        group_id = str(group.id)
        org_name = self.group_org_names.get(str(group.org_id), '')
        display_name = group.name
        if self.org.is_root() and org_name:
            display_name = f'{group.name} ({org_name})'
        return {
            'id': group_id,
            'pId': self.org_id,
            'name': display_name,
            'label': display_name,
            'username': '',
            'hasChildren': has_children,
            'isParent': has_children,
            '_isLeaf': not has_children,
            'meta': self._node_meta(
                'user_group', group.id, name=group.name,
                org_id=str(group.org_id), org_name=org_name,
            ),
        }

    def _set_group_org_names(self, groups):
        org_ids = {str(group.org_id) for group in groups}
        if not org_ids:
            return
        if not self.org.is_root():
            self.group_org_names.update({self.org_id: str(self.org.name)})
            return
        valid_org_ids = []
        for org_id in org_ids:
            try:
                valid_org_ids.append(UUID(org_id))
            except (TypeError, ValueError):
                self.group_org_names[org_id] = str(self.org.name)
        rows = Organization.objects.filter(id__in=valid_org_ids).values_list(
            'id', 'name'
        )
        self.group_org_names.update(
            {str(org_id): name for org_id, name in rows}
        )

    @staticmethod
    def _user_node(user, parent_id, parent_type='user_group'):
        user_id = str(user.id)
        parent_id = str(parent_id)
        return {
            'id': f'user:{parent_id}:{user_id}',
            'pId': parent_id,
            'name': user.name or user.username,
            'username': user.username,
            'hasChildren': False,
            'isParent': False,
            '_isLeaf': True,
            'meta': UserGroupTree._node_meta(
                'user', user.id, name=user.name, username=user.username,
                parent_id=parent_id, parent_type=parent_type,
            ),
        }

    def _ordered_users(self, queryset, order):
        fields = ('username', 'name', 'id') if order == 'username' else (
            'name', 'username', 'id'
        )
        return queryset.order_by(*fields)

    def _ungrouped_users(self):
        group_ids = self.groups.values('id')
        return self.users.exclude(groups__id__in=group_ids).distinct()

    def root(self):
        has_children = self.groups.exists() or self.users.exists()
        return [self._organization_node(has_children)]

    def children(
        self, parent_type, parent_id, order='name', limit=1000, offset=0
    ):
        if parent_type == 'organization':
            if str(parent_id) != self.org_id:
                return self._result_envelope(
                    [], limit, False, offset=offset, paginated=True
                )
            ordered_groups = self.groups.order_by('name', 'org_id', 'id')
            group_count = ordered_groups.count()
            group_limit = min(limit, max(group_count - offset, 0))
            groups = list(ordered_groups[offset:offset + group_limit])
            self._set_group_org_names(groups)
            group_ids = [group.id for group in groups]
            groups_with_users = set(
                User.groups.through.objects.filter(
                    usergroup_id__in=group_ids,
                    user_id__in=self.users.values('id'),
                ).values_list('usergroup_id', flat=True).distinct()
            )
            nodes = [
                self._group_node(group, group.id in groups_with_users)
                for group in groups
            ]
            remaining = limit - len(nodes)
            user_offset = max(offset - group_count, 0)
            ungrouped = self._ordered_users(self._ungrouped_users(), order)
            user_candidates = []
            if remaining:
                user_candidates = list(
                    ungrouped[user_offset:user_offset + remaining + 1]
                )
                users = user_candidates[:remaining]
                nodes.extend(
                    self._user_node(
                        user, self.org_id, parent_type='organization'
                    )
                    for user in users
                )
            groups_remain = offset + len(groups) < group_count
            if groups_remain:
                truncated = True
            elif remaining:
                truncated = len(user_candidates) > remaining
            else:
                truncated = ungrouped[user_offset:user_offset + 1].exists()
            matched_user_count = sum(
                node['meta']['type'] == 'user' for node in nodes
            )
            return self._result_envelope(
                nodes, limit, truncated, offset=offset, paginated=True,
                matched_user_count=matched_user_count,
            )

        group = self.groups.filter(id=parent_id).first()
        if group is None:
            return self._result_envelope(
                [], limit, False, offset=offset, paginated=True
            )
        self._set_group_org_names([group])
        queryset = self._ordered_users(
            self.users.filter(groups__id=group.id).distinct(), order
        )
        candidates = list(
            queryset[offset:offset + limit + 1]
        )
        users = candidates[:limit]
        nodes = [self._user_node(user, group.id) for user in users]
        return self._result_envelope(
            nodes, limit, len(candidates) > limit,
            offset=offset, paginated=True,
            matched_user_count=len(nodes),
        )

    def search(self, keyword, order='name', limit=1000):
        user_query = Q(name__icontains=keyword) | Q(username__icontains=keyword)
        current_group_ids = self.groups.values('id')
        primary_group = (
            User.groups.through.objects.filter(
                user_id=OuterRef('pk'),
                usergroup_id__in=current_group_ids,
            )
            .order_by('usergroup__name', 'usergroup__org_id', 'usergroup_id')
            .values('usergroup_id')[:1]
        )
        matched_user_candidates = list(
            self._ordered_users(
                self.users.filter(user_query).annotate(
                    tree_parent_group_id=Subquery(primary_group)
                ),
                order,
            )[:limit + 1]
        )
        users_truncated = len(matched_user_candidates) > limit
        matched_users = matched_user_candidates[:limit]

        matching_group_candidates = list(
            self.groups.filter(name__icontains=keyword)
            .order_by('name', 'org_id', 'id')
            .values_list('id', flat=True)[:limit + 1]
        )
        groups_truncated = len(matching_group_candidates) > limit
        matching_group_ids = matching_group_candidates[:limit]
        matching_group_id_set = set(matching_group_ids)
        parent_group_ids = {
            user.tree_parent_group_id for user in matched_users
            if user.tree_parent_group_id is not None
        }
        result_group_ids = matching_group_id_set | parent_group_ids
        if not result_group_ids and not matched_users:
            return self._result_envelope([], limit, False)

        groups = list(
            self.groups.filter(id__in=result_group_ids)
            .order_by('name', 'org_id', 'id')
        )
        self._set_group_org_names(groups)
        groups_with_users = set(
            User.groups.through.objects.filter(
                usergroup_id__in=result_group_ids,
                user_id__in=self.users.values('id'),
            ).values_list('usergroup_id', flat=True).distinct()
        )
        users_by_id = {user.id: user for user in matched_users}
        user_ids_by_group = defaultdict(list)
        for user in matched_users:
            if user.tree_parent_group_id is not None:
                user_ids_by_group[user.tree_parent_group_id].append(user.id)

        nodes = [self._organization_node(True)]
        visible_user_ids = set()
        # A user occurrence needs its parent branch, so keep a bounded 2:1
        # visual-node budget while preserving `limit` as the unique-user cap.
        remaining = limit * 2
        budget_truncated = False
        resolved_parent_ids = {group.id for group in groups}
        parent_groups = [
            group for group in groups if group.id in parent_group_ids
        ]
        matching_only_groups = [
            group for group in groups if group.id not in parent_group_ids
        ]
        for group in parent_groups:
            user_ids = user_ids_by_group[group.id]
            nodes.append(
                self._group_node(group, group.id in groups_with_users)
            )
            remaining -= 1
            users = [users_by_id[user_id] for user_id in user_ids]
            users.sort(
                key=lambda user: (
                    getattr(user, order) or '', user.name or '',
                    user.username or '', str(user.id),
                )
            )
            visible_users = users[:remaining]
            nodes.extend(
                self._user_node(user, group.id) for user in visible_users
            )
            visible_user_ids.update(user.id for user in visible_users)
            remaining -= len(visible_users)
            if len(visible_users) < len(users):
                budget_truncated = True
                break

        ungrouped_users = [
            user for user in matched_users
            if user.tree_parent_group_id is None
            or user.tree_parent_group_id not in resolved_parent_ids
        ]
        if ungrouped_users and remaining:
            visible_users = ungrouped_users[:remaining]
            nodes.extend(
                self._user_node(
                    user, self.org_id, parent_type='organization'
                )
                for user in visible_users
            )
            visible_user_ids.update(user.id for user in visible_users)
            remaining -= len(visible_users)
            if len(visible_users) < len(ungrouped_users):
                budget_truncated = True
        elif ungrouped_users:
            budget_truncated = True

        for group in matching_only_groups:
            if remaining == 0:
                budget_truncated = True
                break
            nodes.append(
                self._group_node(group, group.id in groups_with_users)
            )
            remaining -= 1

        truncated = any((
            users_truncated,
            groups_truncated,
            budget_truncated,
        ))
        return self._result_envelope(
            nodes, limit, truncated,
            matched_user_count=len(visible_user_ids),
        )

    @staticmethod
    def _result_envelope(
        results, limit, truncated, offset=0, paginated=False,
        matched_user_count=0,
    ):
        return {
            'results': results,
            'limit': limit,
            'offset': offset,
            'next_offset': (
                offset + len(results) if paginated and truncated else None
            ),
            'returned_count': len(results),
            'matched_user_count': matched_user_count,
            'truncated': truncated,
            'has_more': truncated,
        }
