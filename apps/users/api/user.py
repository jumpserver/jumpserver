# ~*~ coding: utf-8 ~*~
import uuid

from django.core.cache import cache
from django.contrib.auth import logout
from django.utils.translation import ugettext as _

from rest_framework import generics
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_bulk import BulkModelViewSet

from ..serializers import UserSerializer, UserPKUpdateSerializer, \
    UserUpdateGroupSerializer, ChangeUserPasswordSerializer
from ..models import User
from orgs.utils import current_org
from common.permissions import IsOrgAdmin, IsCurrentUserOrReadOnly, IsOrgAdminOrAppUser
from common.mixins import IDInFilterMixin
from common.utils import get_logger


logger = get_logger(__name__)
__all__ = [
    'UserViewSet', 'UserChangePasswordApi', 'UserUpdateGroupApi',
    'UserResetPasswordApi', 'UserResetPKApi', 'UserUpdatePKApi',
    'UserUnblockPKApi', 'UserProfileApi', 'UserResetOTPApi',
]


class UserViewSet(IDInFilterMixin, BulkModelViewSet):
    queryset = User.objects.exclude(role="App")
    serializer_class = UserSerializer
    permission_classes = (IsOrgAdmin,)
    filter_fields = ('username', 'email', 'name', 'id')

    def get_queryset(self):
        queryset = super().get_queryset()
        org_users = current_org.get_org_users()
        queryset = queryset.filter(id__in=org_users)
        return queryset

    def get_permissions(self):
        if self.action == "retrieve":
            self.permission_classes = (IsOrgAdminOrAppUser,)
        return super().get_permissions()


class UserChangePasswordApi(generics.RetrieveUpdateAPIView):
    permission_classes = (IsOrgAdmin,)
    queryset = User.objects.all()
    serializer_class = ChangeUserPasswordSerializer

    def perform_update(self, serializer):
        user = self.get_object()
        user.password_raw = serializer.validated_data["password"]
        user.save()


class UserUpdateGroupApi(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserUpdateGroupSerializer
    permission_classes = (IsOrgAdmin,)


class UserResetPasswordApi(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def perform_update(self, serializer):
        # Note: we are not updating the user object here.
        # We just do the reset-password stuff.
        from ..utils import send_reset_password_mail
        user = self.get_object()
        user.password_raw = str(uuid.uuid4())
        user.save()
        send_reset_password_mail(user)


class UserResetPKApi(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def perform_update(self, serializer):
        from ..utils import send_reset_ssh_key_mail
        user = self.get_object()
        user.is_public_key_valid = False
        user.save()
        send_reset_ssh_key_mail(user)


class UserUpdatePKApi(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserPKUpdateSerializer
    permission_classes = (IsCurrentUserOrReadOnly,)

    def perform_update(self, serializer):
        user = self.get_object()
        user.public_key = serializer.validated_data['_public_key']
        user.save()


class UserUnblockPKApi(generics.UpdateAPIView):
    queryset = User.objects.all()
    permission_classes = (IsOrgAdmin,)
    serializer_class = UserSerializer
    key_prefix_limit = "_LOGIN_LIMIT_{}_{}"
    key_prefix_block = "_LOGIN_BLOCK_{}"

    def perform_update(self, serializer):
        user = self.get_object()
        username = user.username if user else ''
        key_limit = self.key_prefix_limit.format(username, '*')
        key_block = self.key_prefix_block.format(username)
        cache.delete_pattern(key_limit)
        cache.delete(key_block)


class UserProfileApi(generics.RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class UserResetOTPApi(generics.RetrieveAPIView):
    queryset = User.objects.all()
    permission_classes = (IsOrgAdmin,)

    def retrieve(self, request, *args, **kwargs):
        user = self.get_object() if kwargs.get('pk') else request.user
        if user == request.user:
            msg = _("Could not reset self otp, use profile reset instead")
            return Response({"error": msg}, status=401)
        if user.otp_enabled and user.otp_secret_key:
            user.otp_secret_key = ''
            user.save()
            logout(request)
        return Response({"msg": "success"})
