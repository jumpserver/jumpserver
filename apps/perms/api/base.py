from django.db.models import Q
from common.permissions import IsOrgAdmin
from common.utils import get_object_or_none
from orgs.mixins.api import OrgBulkModelViewSet
from assets.models import SystemUser
from users.models import User, UserGroup


__all__ = ['BasePermissionViewSet']


class BasePermissionViewSet(OrgBulkModelViewSet):
    custom_filter_fields = [
        'user_id', 'username', 'system_user_id', 'system_user',
        'user_group_id', 'user_group'
    ]
    permission_classes = (IsOrgAdmin,)

    def filter_valid(self, queryset):
        valid_query = self.request.query_params.get('is_valid', None)
        if valid_query is None:
            return queryset
        invalid = valid_query in ['0', 'N', 'false', 'False']
        if invalid:
            queryset = queryset.invalid()
        else:
            queryset = queryset.valid()
        return queryset

    def is_query_all(self):
        query_all = self.request.query_params.get('all', '1') == '1'
        return query_all

    def filter_user(self, queryset):
        user_id = self.request.query_params.get('user_id')
        username = self.request.query_params.get('username')
        if user_id:
            user = get_object_or_none(User, pk=user_id)
        elif username:
            user = get_object_or_none(User, username=username)
        else:
            return queryset
        if not user:
            return queryset.none()
        if not self.is_query_all():
            queryset = queryset.filter(users=user)
            return queryset
        groups = list(user.groups.all().values_list('id', flat=True))
        queryset = queryset.filter(
            Q(users=user) | Q(user_groups__in=groups)
        ).distinct()
        return queryset

    def filter_keyword(self, queryset):
        keyword = self.request.query_params.get('search')
        if not keyword:
            return queryset
        queryset = queryset.filter(name__icontains=keyword)
        return queryset

    def filter_system_user(self, queryset):
        system_user_id = self.request.query_params.get('system_user_id')
        system_user_name = self.request.query_params.get('system_user')
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
        user_group_id = self.request.query_params.get('user_group_id')
        user_group_name = self.request.query_params.get('user_group')
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

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        queryset = self.filter_valid(queryset)
        queryset = self.filter_user(queryset)
        queryset = self.filter_system_user(queryset)
        queryset = self.filter_user_group(queryset)
        queryset = self.filter_keyword(queryset)
        queryset = queryset.distinct()
        return queryset
