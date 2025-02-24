from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext as _
from django_filters import rest_framework as filters

from common.drf.filters import BaseFilterSet
from common.utils import is_uuid
from jumpserver import settings
from rbac.models import Role, OrgRoleBinding, SystemRoleBinding
from users.models.user import User


class UserFilter(BaseFilterSet):
    system_roles = filters.CharFilter(method='filter_system_roles')
    org_roles = filters.CharFilter(method='filter_org_roles')
    groups = filters.CharFilter(field_name="groups__name", lookup_expr='exact')
    group_id = filters.CharFilter(field_name="groups__id", lookup_expr='exact')
    exclude_group_id = filters.CharFilter(
        field_name="groups__id", lookup_expr='exact', exclude=True
    )
    is_expired = filters.BooleanFilter(method='filter_is_expired')
    is_valid = filters.BooleanFilter(method='filter_is_valid')
    is_password_expired = filters.BooleanFilter(method='filter_long_time')
    is_long_time_no_login = filters.BooleanFilter(method='filter_long_time')
    is_login_blocked = filters.BooleanFilter(method='filter_is_blocked')

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'name',
            'groups', 'group_id', 'exclude_group_id',
            'source', 'org_roles', 'system_roles',
            'is_active', 'is_first_login',
        )

    def filter_is_blocked(self, queryset, name, value):
        from users.utils import LoginBlockUtil
        usernames = LoginBlockUtil.get_blocked_usernames()
        if value:
            queryset = queryset.filter(username__in=usernames)
        else:
            queryset = queryset.exclude(username__in=usernames)
        return queryset

    def filter_long_time(self, queryset, name, value):
        now = timezone.now()
        if name == 'is_password_expired':
            interval = settings.SECURITY_PASSWORD_EXPIRATION_TIME
        else:
            interval = 30
        date_expired = now - timezone.timedelta(days=int(interval))

        if name == 'is_password_expired':
            key = 'date_password_last_updated'
        elif name == 'is_long_time_no_login':
            key = 'last_login'
        else:
            raise ValueError('Invalid filter name')

        if value:
            kwargs = {f'{key}__lt': date_expired}
        else:
            kwargs = {f'{key}__gt': date_expired}
        q = Q(**kwargs) | Q(**{f'{key}__isnull': True})
        return queryset.filter(q)

    def filter_is_valid(self, queryset, name, value):
        if value:
            queryset = self.filter_is_expired(queryset, name, False).filter(is_active=True)
        else:
            q = Q(date_expired__lt=timezone.now()) | Q(is_active=False)
            queryset = queryset.filter(q)
        return queryset

    @staticmethod
    def filter_is_expired(queryset, name, value):
        now = timezone.now()
        if value:
            queryset = queryset.filter(date_expired__lt=now)
        else:
            queryset = queryset.filter(date_expired__gte=now)
        return queryset

    @staticmethod
    def _get_role(value):
        from rbac.builtin import BuiltinRole
        roles = BuiltinRole.get_roles()
        for role in roles.values():
            if _(role.name) == value:
                return role

        if is_uuid(value):
            return Role.objects.filter(id=value).first()
        else:
            return Role.objects.filter(name=value).first()

    def _filter_roles(self, queryset, value, scope):
        role = self._get_role(value)
        if not role:
            return queryset.none()

        rb_model = SystemRoleBinding if scope == Role.Scope.system.value else OrgRoleBinding
        user_ids = rb_model.objects.filter(role_id=role.id).values_list('user_id', flat=True)
        queryset = queryset.filter(id__in=user_ids).distinct()
        return queryset

    def filter_system_roles(self, queryset, name, value):
        queryset = self._filter_roles(queryset=queryset, value=value, scope=Role.Scope.system.value)
        return queryset

    def filter_org_roles(self, queryset, name, value):
        queryset = self._filter_roles(queryset=queryset, value=value, scope=Role.Scope.org.value)
        return queryset
