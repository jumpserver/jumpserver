from django_filters import rest_framework as filters
from django.db.models import QuerySet, Q

from common.drf.filters import BaseFilterSet
from common.utils import get_object_or_none
from users.models import User, UserGroup
from assets.models import Node, Asset, SystemUser
from perms.models import AssetPermission


class PermissionBaseFilter(BaseFilterSet):
    is_valid = filters.BooleanFilter(method='do_nothing')
    user_id = filters.UUIDFilter(method='do_nothing')
    username = filters.CharFilter(method='do_nothing')
    system_user_id = filters.UUIDFilter(method='do_nothing')
    system_user = filters.CharFilter(method='do_nothing')
    user_group_id = filters.UUIDFilter(method='do_nothing')
    user_group = filters.CharFilter(method='do_nothing')
    all = filters.BooleanFilter(method='do_nothing')

    class Meta:
        fields = (
            'user_id', 'username', 'system_user_id', 'system_user', 'user_group_id',
            'user_group', 'name', 'all', 'is_valid',
        )

    @property
    def qs(self):
        qs = super().qs
        qs = self.filter_valid(qs)
        qs = self.filter_user(qs)
        qs = self.filter_system_user(qs)
        qs = self.filter_user_group(qs)
        return qs

    def filter_valid(self, queryset):
        is_valid = self.get_query_param('is_valid')
        if is_valid is None:
            return queryset

        if is_valid:
            queryset = queryset.valid()
        else:
            queryset = queryset.invalid()
        return queryset

    def filter_user(self, queryset):
        is_query_all = self.get_query_param('all', True)
        user_id = self.get_query_param('user_id')
        username = self.get_query_param('username')

        if user_id:
            user = get_object_or_none(User, pk=user_id)
        elif username:
            user = get_object_or_none(User, username=username)
        else:
            return queryset
        if not user:
            return queryset.none()
        if is_query_all:
            queryset = queryset.filter(users=user)
            return queryset
        groups = list(user.groups.all().values_list('id', flat=True))
        queryset = queryset.filter(
            Q(users=user) | Q(user_groups__in=groups)
        ).distinct()
        return queryset

    def filter_system_user(self, queryset):
        system_user_id = self.get_query_param('system_user_id')
        system_user_name = self.get_query_param('system_user')

        if system_user_id:
            system_user = get_object_or_none(SystemUser, pk=system_user_id)
        elif system_user_name:
            system_user = get_object_or_none(SystemUser, name=system_user_name)
        else:
            return queryset
        if not system_user:
            return queryset.none()
        queryset = queryset.filter(system_users=system_user)
        return queryset

    def filter_user_group(self, queryset):
        user_group_id = self.get_query_param('user_group_id')
        user_group_name = self.get_query_param('user_group')

        if user_group_id:
            group = get_object_or_none(UserGroup, pk=user_group_id)
        elif user_group_name:
            group = get_object_or_none(UserGroup, name=user_group_name)
        else:
            return queryset
        if not group:
            return queryset.none()
        queryset = queryset.filter(user_groups=group)
        return queryset


class AssetPermissionFilter(PermissionBaseFilter):
    is_effective = filters.BooleanFilter(method='do_nothing')
    node_id = filters.UUIDFilter(method='do_nothing')
    node = filters.CharFilter(method='do_nothing')
    asset_id = filters.UUIDFilter(method='do_nothing')
    hostname = filters.CharFilter(method='do_nothing')
    ip = filters.CharFilter(method='do_nothing')

    class Meta:
        model = AssetPermission
        fields = (
            'user_id', 'username', 'system_user_id', 'system_user', 'user_group_id',
            'user_group', 'node_id', 'node', 'asset_id', 'hostname', 'ip', 'name',
            'all', 'asset_id', 'is_valid', 'is_effective',
        )

    @property
    def qs(self):
        qs = super().qs
        qs = self.filter_effective(qs)
        qs = self.filter_asset(qs)
        qs = self.filter_node(qs)
        return qs

    def filter_node(self, queryset: QuerySet):
        is_query_all = self.get_query_param('all', True)
        node_id = self.get_query_param('node_id')
        node_name = self.get_query_param('node')
        if node_id:
            _nodes = Node.objects.filter(pk=node_id)
        elif node_name:
            _nodes = Node.objects.filter(value=node_name)
        else:
            return queryset
        if not _nodes:
            return queryset.none()

        if not is_query_all:
            queryset = queryset.filter(nodes__in=_nodes)
            return queryset
        nodes = set(_nodes)
        for node in _nodes:
            nodes |= set(node.get_ancestors(with_self=True))
        queryset = queryset.filter(nodes__in=nodes)
        return queryset

    def filter_asset(self, queryset):
        is_query_all = self.get_query_param('all', True)
        asset_id = self.get_query_param('asset_id')
        hostname = self.get_query_param('hostname')
        ip = self.get_query_param('ip')

        if asset_id:
            assets = Asset.objects.filter(pk=asset_id)
        elif hostname:
            assets = Asset.objects.filter(hostname=hostname)
        elif ip:
            assets = Asset.objects.filter(ip=ip)
        else:
            return queryset
        if not assets:
            return queryset.none()
        if not is_query_all:
            queryset = queryset.filter(assets__in=assets)
            return queryset
        inherit_all_nodes = set()
        inherit_nodes_keys = assets.all().values_list('nodes__key', flat=True)

        for key in inherit_nodes_keys:
            if key is None:
                continue
            ancestor_keys = Node.get_node_ancestor_keys(key, with_self=True)
            inherit_all_nodes.update(ancestor_keys)
        queryset = queryset.filter(
            Q(assets__in=assets) | Q(nodes__key__in=inherit_all_nodes)
        ).distinct()
        return queryset

    def filter_effective(self, queryset):
        is_effective = self.get_query_param('is_effective')
        if is_effective is None:
            return queryset

        if is_effective:
            have_user_q = Q(users__isnull=False) | Q(user_groups__isnull=False)
            have_asset_q = Q(assets__isnull=False) | Q(nodes__isnull=False)
            have_system_user_q = Q(system_users__isnull=False)
            have_action_q = Q(actions__gt=0)

            queryset = queryset.filter(
                have_user_q & have_asset_q & have_system_user_q & have_action_q
            )
            queryset &= AssetPermission.objects.valid()
        else:
            not_have_user_q = Q(users__isnull=True) & Q(user_groups__isnull=True)
            not_have_asset_q = Q(assets__isnull=True) & Q(nodes__isnull=True)
            not_have_system_user_q = Q(system_users__isnull=True)
            not_have_action_q = Q(actions=0)

            queryset = queryset.filter(
                not_have_user_q | not_have_asset_q | not_have_system_user_q |
                not_have_action_q
            )
            queryset |= AssetPermission.objects.invalid()
        return queryset
