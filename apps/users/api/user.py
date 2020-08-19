# ~*~ coding: utf-8 ~*~
from django.core.cache import cache
from django.db.models import CharField
from django.utils.translation import ugettext as _

from rest_framework import generics
from rest_framework.response import Response
from rest_framework_bulk import BulkModelViewSet

from common.db.aggregates import GroupConcat
from common.permissions import (
    IsOrgAdmin, IsOrgAdminOrAppUser,
    CanUpdateDeleteUser, IsSuperUser
)
from common.mixins import CommonApiMixin
from common.utils import get_logger
from orgs.utils import current_org
from orgs.models import ROLE as ORG_ROLE, OrganizationMember
from .. import serializers
from ..serializers import UserSerializer, UserRetrieveSerializer
from .mixins import UserQuerysetMixin
from ..models import User
from ..signals import post_user_create
from ..filters import OrgRoleUserFilterBackend


logger = get_logger(__name__)
__all__ = [
    'UserViewSet', 'UserChangePasswordApi',
    'UserUnblockPKApi', 'UserResetOTPApi',
]


class UserViewSet(CommonApiMixin, UserQuerysetMixin, BulkModelViewSet):
    filter_fields = ('username', 'email', 'name', 'id', 'source')
    search_fields = filter_fields
    permission_classes = (IsOrgAdmin, CanUpdateDeleteUser)
    serializer_classes = {
        'default': UserSerializer,
        'retrieve': UserRetrieveSerializer
    }
    extra_filter_backends = [OrgRoleUserFilterBackend]

    def get_queryset(self):
        return super().get_queryset().annotate(
            gc_m2m_org_members__role=GroupConcat('m2m_org_members__role'),
            gc_groups__name=GroupConcat('groups__name'),
            gc_groups=GroupConcat('groups__id', output_field=CharField())
        )

    def send_created_signal(self, users):
        if not isinstance(users, list):
            users = [users]
        for user in users:
            post_user_create.send(self.__class__, user=user)

    def perform_create(self, serializer):
        validated_data = serializer.validated_data

        # `org_roles` 先 `pop`
        if isinstance(validated_data, list):
            org_roles = [item.pop('org_roles', []) for item in validated_data]
        else:
            org_roles = [validated_data.pop('org_roles', [])]

        # 创建用户
        users = serializer.save()
        if isinstance(users, User):
            users = [users]

        # 只有真实存在的组织才真正关联用户
        if current_org and current_org.is_real():
            for user, roles in zip(users, org_roles):
                if not roles:
                    # 当前组织创建的用户，至少是该组织的`User`
                    roles.append(ORG_ROLE.USER)
                OrganizationMember.objects.set_user_roles(current_org, user, roles)
        self.send_created_signal(users)

    def get_permissions(self):
        if self.action in ["retrieve", "list"]:
            self.permission_classes = (IsOrgAdminOrAppUser,)
        if self.request.query_params.get('all'):
            self.permission_classes = (IsSuperUser,)
        return super().get_permissions()

    def perform_destroy(self, instance):
        if current_org.is_real():
            instance.remove()
        else:
            return super().perform_destroy(instance)

    def perform_bulk_destroy(self, objects):
        for obj in objects:
            self.check_object_permissions(self.request, obj)
            self.perform_destroy(obj)

    def perform_update(self, serializer):
        validated_data = serializer.validated_data
        # `org_roles` 先 `pop`
        if isinstance(validated_data, list):
            org_roles = [item.pop('org_roles', None) for item in validated_data]
        else:
            org_roles = [validated_data.pop('org_roles', None)]

        users = serializer.save()
        if isinstance(users, User):
            users = [users]
        if current_org and current_org.is_real():
            for user, roles in zip(users, org_roles):
                if roles is not None:
                    # roles 是 `Node` 表明不需要更新
                    OrganizationMember.objects.set_user_roles(current_org, user, roles)

    def perform_bulk_update(self, serializer):
        # TODO: 需要测试
        users_ids = [
            d.get("id") or d.get("pk") for d in serializer.validated_data
        ]
        users = current_org.get_members().filter(id__in=users_ids)
        for user in users:
            self.check_object_permissions(self.request, user)
        return super().perform_bulk_update(serializer)


class UserChangePasswordApi(UserQuerysetMixin, generics.RetrieveUpdateAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.ChangeUserPasswordSerializer

    def perform_update(self, serializer):
        user = self.get_object()
        user.password_raw = serializer.validated_data["password"]
        user.save()


class UserUnblockPKApi(UserQuerysetMixin, generics.UpdateAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.UserSerializer
    key_prefix_limit = "_LOGIN_LIMIT_{}_{}"
    key_prefix_block = "_LOGIN_BLOCK_{}"

    def perform_update(self, serializer):
        user = self.get_object()
        username = user.username if user else ''
        key_limit = self.key_prefix_limit.format(username, '*')
        key_block = self.key_prefix_block.format(username)
        cache.delete_pattern(key_limit)
        cache.delete(key_block)


class UserResetOTPApi(UserQuerysetMixin, generics.RetrieveAPIView):
    permission_classes = (IsOrgAdmin,)
    serializer_class = serializers.ResetOTPSerializer

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object() if kwargs.get('pk') else request.user
        if user == request.user:
            msg = _("Could not reset self otp, use profile reset instead")
            return Response({"error": msg}, status=401)
        if user.mfa_enabled:
            user.reset_mfa()
            user.save()
        return Response({"msg": "success"})
