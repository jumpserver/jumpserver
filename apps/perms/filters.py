from django.db.models import QuerySet, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_filters import rest_framework as filters

from assets.const import AllTypes, Category, GATEWAY_NAME
from assets.models import Node, Asset
from common.drf.filters import BaseFilterSet
from common.utils import get_object_or_none, is_uuid
from perms.models import AssetPermission, AssetPermissionQuerySet
from users.models import User, UserGroup


class PermedAssetFilterSet(BaseFilterSet):
    platform = filters.CharFilter(
        method='filter_platform', label=_('Platform name or ID')
    )
    type = filters.ChoiceFilter(
        field_name='platform__type', choices=AllTypes.choices(),
        label=_('Platform type')
    )
    category = filters.ChoiceFilter(
        field_name='platform__category', choices=Category.choices,
        label=_('Platform category')
    )
    protocols = filters.CharFilter(
        method='filter_protocols', label=_('Protocols')
    )
    zone = filters.CharFilter(
        method='filter_zone', label=_('Zone name or ID')
    )

    class Meta:
        model = Asset
        fields = [
            'id', 'name', 'address', 'platform', 'type', 'category', 'protocols',
            'zone', 'is_active', 'comment',
        ]
        fields_operator = {
            'platform': ('exact',),
            'category': ('in',),
            'protocols': ('in',),
            'zone': ('icontains',),
        }

    @staticmethod
    def filter_platform(queryset, name, value):
        if value.isdigit():
            return queryset.filter(platform_id=value)
        if value == GATEWAY_NAME:
            return queryset.filter(
                platform__name__istartswith=GATEWAY_NAME
            )
        return queryset.filter(platform__name=value)

    @staticmethod
    def filter_protocols(queryset, name, value):
        protocols = value.split(',')
        return queryset.filter(protocols__name__in=protocols).distinct()

    @staticmethod
    def filter_zone(queryset, name, value):
        if is_uuid(value):
            return queryset.filter(zone_id=value)
        return queryset.filter(zone__name__icontains=value)


class PermissionBaseFilter(BaseFilterSet):
    is_valid = filters.BooleanFilter(
        method='do_nothing', label=_('Is valid')
    )
    is_expired = filters.BooleanFilter(
        method='filter_expired', label=_('Is expired')
    )
    user_id = filters.UUIDFilter(method='do_nothing', label=_('User ID'))
    username = filters.CharFilter(method='do_nothing', label=_('Username'))
    user_group_id = filters.UUIDFilter(
        method='do_nothing', label=_('User group ID')
    )
    user_group = filters.CharFilter(
        field_name='user_groups__name', method='do_nothing',
        label=_('User group name')
    )
    all = filters.BooleanFilter(method='do_nothing', label=_('All'))

    class Meta:
        fields = (
            'user_id', 'username', 'user_group_id', 'user_group', 'name',
            'all', 'is_valid', 'is_expired',
        )

    @property
    def qs(self):
        qs = super().qs
        qs = self.filter_valid(qs)
        qs = self.filter_user(qs)
        qs = self.filter_user_group(qs)
        return qs

    @staticmethod
    def filter_expired(queryset, name, is_expired):
        now = timezone.now()
        if is_expired:
            queryset = queryset.filter(Q(date_start__gt=now) | Q(date_expired__lt=now))
        else:
            queryset = queryset.filter(Q(date_start__lt=now) | Q(date_expired__gt=now))
        return queryset

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

        if not is_query_all:
            queryset = queryset.filter(users=user)
            return queryset
        groups = list(user.groups.all().values_list('id', flat=True))

        user_asset_perm_ids = AssetPermission.objects.filter(users=user).distinct().values_list('id', flat=True)
        group_asset_perm_ids = AssetPermission.objects.filter(user_groups__in=groups).distinct().values_list('id',
                                                                                                             flat=True)

        asset_perm_ids = {*user_asset_perm_ids, *group_asset_perm_ids}

        queryset = queryset.filter(
            id__in=asset_perm_ids
        ).distinct()
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
    is_effective = filters.BooleanFilter(
        method='do_nothing', label=_('Is effective')
    )
    node_id = filters.UUIDFilter(method='do_nothing', label=_('Node ID'))
    node_name = filters.CharFilter(
        method='do_nothing', label=_('Node name')
    )
    asset_id = filters.UUIDFilter(method='do_nothing', label=_('Asset ID'))
    asset_name = filters.CharFilter(
        field_name='assets__name', method='do_nothing',
        label=_('Asset name')
    )
    address = filters.CharFilter(method='do_nothing', label=_('Asset address'))
    accounts = filters.CharFilter(method='do_nothing', label=_('Accounts'))
    is_no_resource = filters.BooleanFilter(
        method='filter_no_resource', label=_('No resource')
    )

    class Meta:
        model = AssetPermission
        fields = (
            'id', 'name', 'all', 
            'user_id', 'username', 'user_group_id', 'user_group',
            'node_id', 'node_name', 'asset_id', 'asset_name',
            'address', 'accounts',
            'is_active', 'is_valid', 'is_expired',
            'is_effective', 'is_no_resource', 'from_ticket',
        )
        fields_operator = {
            'accounts': ('in',),
        }

    @property
    def qs(self):
        qs = super().qs
        qs = self.filter_effective(qs)
        qs = self.filter_asset(qs)
        qs = self.filter_node(qs)
        qs = self.filter_accounts(qs)
        qs = qs.distinct()
        return qs

    def filter_accounts(self, queryset: AssetPermissionQuerySet):
        accounts = self.get_query_param('accounts')
        if not accounts:
            return queryset
        accounts = accounts.split(',')
        queryset = queryset.filter_by_accounts(accounts)
        return queryset

    def filter_node(self, queryset: QuerySet):
        is_query_all = self.get_query_param('all', True)
        node_id = self.get_query_param('node_id')
        node_name = self.get_query_param('node_name')
        if node_id:
            _nodes = Node.objects.filter(pk=node_id)
        elif node_name:
            _nodes = Node.objects.filter(value=node_name)
        else:
            return queryset
        if not _nodes:
            return queryset.none()

        node = _nodes.first()

        if not is_query_all:
            queryset = queryset.filter(nodes=node)
            return queryset
        nodeids = node.get_ancestors(with_self=True).values_list('id', flat=True)
        nodeids = list(nodeids)

        queryset = queryset.filter(nodes__in=nodeids)
        return queryset

    def filter_asset(self, queryset):
        is_query_all = self.get_query_param('all', True)
        asset_id = self.get_query_param('asset_id')
        asset_name = self.get_query_param('asset_name')
        address = self.get_query_param('address')

        if asset_id:
            assets = Asset.objects.filter(pk=asset_id)
        elif asset_name:
            assets = Asset.objects.filter(name=asset_name)
        elif address:
            assets = Asset.objects.filter(address=address)
        else:
            return queryset
        if not assets:
            return queryset.none()
        asset_ids = list(assets.values_list('id', flat=True))

        if not is_query_all:
            queryset = queryset.filter(assets__in=asset_ids)
            return queryset
        inherit_all_node_keys = set()
        inherit_node_keys = set(assets.values_list('nodes__key', flat=True))

        for key in inherit_node_keys:
            ancestor_keys = Node.get_node_ancestor_keys(key, with_self=True)
            inherit_all_node_keys.update(ancestor_keys)

        inherit_all_node_ids = Node.objects.filter(key__in=inherit_all_node_keys).values_list('id', flat=True)
        inherit_all_node_ids = list(inherit_all_node_ids)

        qs1_ids = queryset.filter(assets__in=asset_ids).distinct().values_list('id', flat=True)
        qs2_ids = queryset.filter(nodes__in=inherit_all_node_ids).distinct().values_list('id', flat=True)
        qs_ids = list(qs1_ids) + list(qs2_ids)
        qs = queryset.filter(id__in=qs_ids)
        return qs

    @staticmethod
    def filter_no_resource(queryset, name, value):
        not_have_user_q = Q(users__isnull=True) & Q(user_groups__isnull=True)
        not_have_asset_q = Q(assets__isnull=True) & Q(nodes__isnull=True)
        not_have_action_q = Q(actions=0)
        q = not_have_user_q | not_have_asset_q | not_have_action_q

        if value:
            queryset = queryset.filter(q)
        else:
            queryset = queryset.exclude(q)
        return queryset

    def filter_effective(self, queryset):
        is_effective = self.get_query_param('is_effective')
        if is_effective is None:
            return queryset

        if is_effective:
            have_user_q = Q(users__isnull=False) | Q(user_groups__isnull=False)
            have_asset_q = Q(assets__isnull=False) | Q(nodes__isnull=False)
            have_action_q = Q(actions__gt=0)

            valid_ids = AssetPermission.objects.valid().values_list('pk', flat=True)
            queryset = queryset.filter(have_user_q & have_asset_q & have_action_q)
            queryset = queryset.filter(pk__in=valid_ids)
        else:
            not_have_user_q = Q(users__isnull=True) & Q(user_groups__isnull=True)
            not_have_asset_q = Q(assets__isnull=True) & Q(nodes__isnull=True)
            not_have_action_q = Q(actions=0)

            invalid_ids = AssetPermission.objects.invalid().values_list('pk', flat=True)
            condition_q = not_have_user_q | not_have_asset_q | not_have_action_q | Q(pk__in=invalid_ids)
            queryset = queryset.filter(condition_q)
        return queryset
