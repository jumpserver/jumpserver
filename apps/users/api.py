# ~*~ coding: utf-8 ~*~
#

from django.shortcuts import get_object_or_404

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_bulk import ListBulkCreateUpdateDestroyAPIView

from common.mixins import BulkDeleteApiMixin
from common.utils import get_logger
from .models import User, UserGroup
from .serializers import UserDetailSerializer, UserAndGroupSerializer, \
    GroupDetailSerializer, UserPKUpdateSerializer, UserBulkUpdateSerializer, GroupBulkUpdateSerializer
from .backends import IsSuperUser, IsAppUser, IsValidUser, IsSuperUserOrAppUser


logger = get_logger(__name__)


class UserDetailApi(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserDetailSerializer
    permission_classes = (IsSuperUser,)


class UserAndGroupEditApi(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserAndGroupSerializer
    permission_classes = (IsSuperUser,)


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
    permission_classes = (IsSuperUserOrAppUser,)

    # def get(self, request, *args, **kwargs):
    #     return super(UserListUpdateApi, self).get(request, *args, **kwargs)


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


class AppUserRegisterApi(generics.CreateAPIView):
    """App send a post request to register a app user

    request params contains `username_signed`, You can unsign it,
    username = unsign(username_signed), if you get the username,
    It's present it's a valid request, or return (401, Invalid request),
    then your should check if the user exist or not. If exist,
    return (200, register success), If not, you should be save it, and
    notice admin user, The user default is not active before admin user
    unblock it.

    Save fields:
        username:
        name: name + request.ip
        email: username + '@app.org'
        role: App
    """
    pass
