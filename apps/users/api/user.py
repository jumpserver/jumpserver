# ~*~ coding: utf-8 ~*~
from collections import defaultdict

from django.utils.translation import gettext as _
from rest_framework import generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_bulk import BulkModelViewSet

from common.api import CommonApiMixin, SuggestionMixin
from common.drf.filters import AttrRulesFilterBackend
from common.utils import get_logger
from orgs.utils import current_org, tmp_to_root_org
from rbac.models import Role, RoleBinding
from rbac.permissions import RBACPermission
from users.utils import LoginBlockUtil, MFABlockUtils
from .mixins import UserQuerysetMixin
from .. import serializers
from ..exceptions import UnableToDeleteAllUsers
from ..filters import UserFilter
from ..models import User
from ..notifications import ResetMFAMsg
from ..permissions import UserObjectPermission
from ..serializers import (
    UserSerializer,
    MiniUserSerializer, InviteSerializer
)
from ..signals import post_user_create

logger = get_logger(__name__)
__all__ = [
    'UserViewSet', 'UserChangePasswordApi',
    'UserUnblockPKApi', 'UserResetMFAApi',
]


class UserViewSet(CommonApiMixin, UserQuerysetMixin, SuggestionMixin, BulkModelViewSet):
    filterset_class = UserFilter
    extra_filter_backends = [AttrRulesFilterBackend]
    search_fields = ('username', 'email', 'name')
    permission_classes = [RBACPermission, UserObjectPermission]
    serializer_classes = {
        'default': UserSerializer,
        'suggestion': MiniUserSerializer,
        'invite': InviteSerializer,
    }
    ordering = ('name',)
    rbac_perms = {
        'match': 'users.match_user',
        'invite': 'users.invite_user',
        'remove': 'users.remove_user',
        'bulk_remove': 'users.remove_user',
    }

    def allow_bulk_destroy(self, qs, filtered):
        is_valid = filtered.count() < qs.count()
        if not is_valid:
            raise UnableToDeleteAllUsers()
        return True

    @action(methods=['get'], detail=False, url_path='suggestions')
    def match(self, request, *args, **kwargs):
        with tmp_to_root_org():
            return super().match(request, *args, **kwargs)

    def get_serializer(self, *args, **kwargs):
        """重写 get_serializer，用于设置用户的角色缓存
        放到 paginate_queryset 里面会导致 导出有问题， 因为导出的时候，没有 pager
        """
        if len(args) == 1 and kwargs.get('many'):
            queryset = self.set_users_roles_for_cache(args[0])
            args = (queryset,)
        return super().get_serializer(*args, **kwargs)

    @staticmethod
    def set_users_roles_for_cache(queryset):
        # Todo: 未来有机会用 SQL 实现
        queryset_list = queryset
        user_ids = [u.id for u in queryset_list]
        role_bindings = RoleBinding.objects.filter(user__in=user_ids) \
            .values('user_id', 'role_id', 'scope')

        role_mapper = {r.id: r for r in Role.objects.all()}
        user_org_role_mapper = defaultdict(set)
        user_system_role_mapper = defaultdict(set)

        for binding in role_bindings:
            role_id = binding['role_id']
            user_id = binding['user_id']
            if binding['scope'] == RoleBinding.Scope.system:
                user_system_role_mapper[user_id].add(role_mapper[role_id])
            else:
                user_org_role_mapper[user_id].add(role_mapper[role_id])

        for u in queryset_list:
            system_roles = user_system_role_mapper[u.id]
            org_roles = user_org_role_mapper[u.id]
            u.org_roles.cache_set(org_roles)
            u.system_roles.cache_set(system_roles)
        return queryset_list

    def perform_create(self, serializer):
        users = serializer.save()
        if isinstance(users, User):
            users = [users]
        self.send_created_signal(users)

    def perform_bulk_update(self, serializer):
        user_ids = [
            d.get("id") or d.get("pk") for d in serializer.validated_data
        ]
        users = current_org.get_members().filter(id__in=user_ids)
        for user in users:
            self.check_object_permissions(self.request, user)
        return super().perform_bulk_update(serializer)

    def perform_bulk_destroy(self, objects):
        for obj in objects:
            self.check_object_permissions(self.request, obj)
            self.perform_destroy(obj)

    @action(methods=['post'], detail=False)
    def invite(self, request):
        if not current_org or current_org.is_root():
            error = {"error": "Not a valid org"}
            return Response(error, status=400)

        serializer_cls = self.get_serializer_class()
        serializer = serializer_cls(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        users = validated_data['users']
        org_roles = validated_data['org_roles']
        has_self = any([str(u.id) == str(request.user.id) for u in users])
        if has_self and not request.user.is_superuser:
            error = {"error": _("Can not invite self")}
            return Response(error, status=400)
        for user in users:
            user.org_roles.set(org_roles)
        return Response(serializer.data, status=201)

    @action(methods=['post'], detail=True)
    def remove(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.remove()
        return Response(status=204)

    @action(methods=['post'], detail=False, url_path='remove')
    def bulk_remove(self, request, *args, **kwargs):
        qs = self.get_queryset()
        filtered = self.filter_queryset(qs)

        for instance in filtered:
            instance.remove()
        return Response(status=204)

    def send_created_signal(self, users):
        if not isinstance(users, list):
            users = [users]
        for user in users:
            post_user_create.send(self.__class__, user=user)


class UserChangePasswordApi(UserQuerysetMixin, generics.UpdateAPIView):
    serializer_class = serializers.ChangeUserPasswordSerializer

    def perform_update(self, serializer):
        user = self.get_object()
        user.password_raw = serializer.validated_data["password"]
        user.save()


class UserUnblockPKApi(UserQuerysetMixin, generics.UpdateAPIView):
    serializer_class = serializers.UserSerializer

    def perform_update(self, serializer):
        user = self.get_object()
        username = user.username if user else ''
        LoginBlockUtil.unblock_user(username)
        MFABlockUtils.unblock_user(username)


class UserResetMFAApi(UserQuerysetMixin, generics.RetrieveAPIView):
    serializer_class = serializers.ResetOTPSerializer

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object() if kwargs.get('pk') else request.user
        if user == request.user:
            msg = _("Could not reset self otp, use profile reset instead")
            return Response({"error": msg}, status=400)

        backends = user.active_mfa_backends_mapper
        for backend in backends.values():
            if backend.can_disable():
                backend.disable()

        ResetMFAMsg(user).publish_async()
        return Response({"msg": "success"})
