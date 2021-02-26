# ~*~ coding: utf-8 ~*~
from django.core.cache import cache
from django.utils.translation import ugettext as _
from rest_framework.decorators import action

from rest_framework import generics
from rest_framework.response import Response
from rest_framework_bulk import BulkModelViewSet
from django.db.models import Prefetch

from common.permissions import (
    IsOrgAdmin, IsOrgAdminOrAppUser,
    CanUpdateDeleteUser, IsSuperUser
)
from common.mixins import CommonApiMixin
from common.utils import get_logger
from orgs.utils import current_org
from orgs.models import ROLE as ORG_ROLE, OrganizationMember
from users.utils import send_reset_mfa_mail
from .. import serializers
from ..serializers import UserSerializer, UserRetrieveSerializer, MiniUserSerializer, InviteSerializer
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
    filterset_fields = ('username', 'email', 'name', 'id', 'source')
    search_fields = filterset_fields
    permission_classes = (IsOrgAdmin, CanUpdateDeleteUser)
    serializer_classes = {
        'default': UserSerializer,
        'retrieve': UserRetrieveSerializer,
        'suggestion': MiniUserSerializer,
        'invite': InviteSerializer,
    }
    extra_filter_backends = [OrgRoleUserFilterBackend]

    def get_queryset(self):
        queryset = super().get_queryset().prefetch_related(
            'groups'
        )
        if current_org.is_real():
            # 为在列表中计算用户在真实组织里的角色
            queryset = queryset.prefetch_related(
                Prefetch(
                    'm2m_org_members',
                    queryset=OrganizationMember.objects.filter(org__id=current_org.id)
                )
            )
        return queryset

    def send_created_signal(self, users):
        if not isinstance(users, list):
            users = [users]
        for user in users:
            post_user_create.send(self.__class__, user=user)

    @staticmethod
    def set_users_to_org(users, org_roles, update=False):
        # 只有真实存在的组织才真正关联用户
        if not current_org or not current_org.is_real():
            return
        for user, roles in zip(users, org_roles):
            if update and roles is None:
                continue
            if not roles:
                # 当前组织创建的用户，至少是该组织的`User`
                roles = [ORG_ROLE.USER]
            OrganizationMember.objects.set_user_roles(current_org, user, roles)

    def perform_create(self, serializer):
        org_roles = self.get_serializer_org_roles(serializer)
        # 创建用户
        users = serializer.save()
        if isinstance(users, User):
            users = [users]
        self.set_users_to_org(users, org_roles)
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

    @staticmethod
    def get_serializer_org_roles(serializer):
        validated_data = serializer.validated_data
        # `org_roles` 先 `pop`
        if isinstance(validated_data, list):
            org_roles = [item.pop('org_roles', None) for item in validated_data]
        else:
            org_roles = [validated_data.pop('org_roles', None)]
        return org_roles

    def perform_update(self, serializer):
        org_roles = self.get_serializer_org_roles(serializer)
        users = serializer.save()
        if isinstance(users, User):
            users = [users]
        self.set_users_to_org(users, org_roles, update=True)

    def perform_bulk_update(self, serializer):
        # TODO: 需要测试
        users_ids = [
            d.get("id") or d.get("pk") for d in serializer.validated_data
        ]
        users = current_org.get_members().filter(id__in=users_ids)
        for user in users:
            self.check_object_permissions(self.request, user)
        return super().perform_bulk_update(serializer)

    @action(methods=['get'], detail=False, permission_classes=(IsOrgAdmin,))
    def suggestion(self, request):
        queryset = User.objects.exclude(role=User.ROLE.APP)
        queryset = self.filter_queryset(queryset)
        queryset = queryset[:3]

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(methods=['post'], detail=False, permission_classes=(IsOrgAdmin,))
    def invite(self, request):
        data = request.data
        if not isinstance(data, list):
            data = [request.data]
        if not current_org or not current_org.is_real():
            error = {"error": "Not a valid org"}
            return Response(error, status=400)

        serializer_cls = self.get_serializer_class()
        serializer = serializer_cls(data=data, many=True)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        for i in validated_data:
            i['org_id'] = current_org.org_id()
        relations = [OrganizationMember(**i) for i in validated_data]
        OrganizationMember.objects.bulk_create(relations, ignore_conflicts=True)
        return Response(serializer.data, status=201)


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
            send_reset_mfa_mail(user)
        return Response({"msg": "success"})
