# ~*~ coding: utf-8 ~*~
#

from django.shortcuts import get_object_or_404

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_bulk import ListBulkCreateUpdateDestroyAPIView

from .models import User, UserGroup
from .serializers import UserDetailSerializer, UserAndGroupSerializer, \
    GroupDetailSerializer, UserPKUpdateSerializer, UserBulkUpdateSerializer, GroupBulkUpdateSerializer
from common.mixins import BulkDeleteApiMixin
from common.utils import get_logger


logger = get_logger(__name__)


class UserDetailApi(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer


class UserAndGroupEditApi(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserAndGroupSerializer


class UserResetPasswordApi(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer

    def perform_update(self, serializer):
        # Note: we are not updating the user object here.
        # We just do the reset-password staff.
        user = self.get_object()
        import uuid
        user.password_raw = str(uuid.uuid4())
        user.save()
        from .utils import send_reset_password_mail
        send_reset_password_mail(user)


class UserResetPKApi(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer

    def perform_update(self, serializer):
        user = self.get_object()
        user.is_public_key_valid = False
        user.save()
        from .utils import send_reset_ssh_key_mail
        send_reset_ssh_key_mail(user)


class UserUpdatePKApi(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserPKUpdateSerializer

    def perform_update(self, serializer):
        user = self.get_object()
        user.private_key = serializer.validated_data['_public_key']
        user.save()


class GroupDetailApi(generics.RetrieveUpdateDestroyAPIView):
    queryset = UserGroup.objects.all()
    serializer_class = GroupDetailSerializer

    def perform_update(self, serializer):
        users = serializer.validated_data.get('users')
        if users:
            group = self.get_object()
            # Note: use `list` method to force hitting the db.
            group_users = list(group.users.all())
            serializer.save()
            group.users.set(users + group_users)
            group.save()
            return
        serializer.save()


class UserListUpdateApi(BulkDeleteApiMixin, ListBulkCreateUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserBulkUpdateSerializer


class GroupListUpdateApi(BulkDeleteApiMixin, ListBulkCreateUpdateDestroyAPIView):
    queryset = UserGroup.objects.all()
    serializer_class = GroupBulkUpdateSerializer


class DeleteUserFromGroupApi(generics.DestroyAPIView):
    queryset = UserGroup.objects.all()
    serializer_class = GroupDetailSerializer

    def destroy(self, request, *args, **kwargs):
        group = self.get_object()
        self.perform_destroy(group, **kwargs)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance, **kwargs):
        user_id = kwargs.get('uid')
        user = get_object_or_404(User, id=user_id)
        instance.users.remove(user)
