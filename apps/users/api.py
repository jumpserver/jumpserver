# ~*~ coding: utf-8 ~*~
#

import base64

from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.conf import settings
from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_bulk import ListBulkCreateUpdateDestroyAPIView, BulkModelViewSet
from rest_framework import authentication

from common.mixins import BulkDeleteApiMixin
from common.utils import get_logger
from .utils import check_user_valid, token_gen
from .models import User, UserGroup
from .hands import write_login_log_async
from .backends import IsSuperUser, IsTerminalUser, IsValidUser, IsSuperUserOrTerminalUser
from . import serializers


logger = get_logger(__name__)


class UserViewSet(BulkModelViewSet):
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer
    permission_classes = (IsSuperUser,)


class UserAndGroupEditApi(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = serializers.UserAndGroupSerializer
    permission_classes = (IsSuperUser,)


class UserResetPasswordApi(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer

    def perform_update(self, serializer):
        # Note: we are not updating the user object here.
        # We just do the reset-password staff.
        import uuid
        from .utils import send_reset_password_mail
        user = self.get_object()
        user.password_raw = str(uuid.uuid4())
        user.save()
        send_reset_password_mail(user)


class UserResetPKApi(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer

    def perform_update(self, serializer):
        from .utils import send_reset_ssh_key_mail
        user = self.get_object()
        user.is_public_key_valid = False
        user.save()
        send_reset_ssh_key_mail(user)


class UserUpdatePKApi(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = serializers.UserPKUpdateSerializer

    def perform_update(self, serializer):
        user = self.get_object()
        user.public_key = serializer.validated_data['_public_key']
        user.save()

#
# class GroupDetailApi(generics.RetrieveUpdateDestroyAPIView):
#     queryset = UserGroup.objects.all()
#     serializer_class = serializers.GroupDetailSerializer
#
#     def perform_update(self, serializer):
#         users = serializer.validated_data.get('users')
#         if users:
#             group = self.get_object()
#             Note: use `list` method to force hitting the db.
            # group_users = list(group.users.all())
            # serializer.save()
            # group.users.set(users + group_users)
            # group.save()
            # return
        # serializer.save()


# class UserListUpdateApi(BulkDeleteApiMixin, ListBulkCreateUpdateDestroyAPIView):
#     queryset = User.objects.all()
#     serializer_class = serializers.UserBulkUpdateSerializer
#     permission_classes = (IsSuperUserOrTerminalUser,)
#
#     def get(self, request, *args, **kwargs):
#         return super(UserListUpdateApi, self).get(request, *args, **kwargs)

#
# class GroupListUpdateApi(BulkDeleteApiMixin, ListBulkCreateUpdateDestroyAPIView):
#     queryset = UserGroup.objects.all()
#     serializer_class = serializers.GroupBulkUpdateSerializer
#

# class DeleteUserFromGroupApi(generics.DestroyAPIView):
#     queryset = UserGroup.objects.all()
#     serializer_class = serializers.GroupDetailSerializer
#
#     def destroy(self, request, *args, **kwargs):
#         group = self.get_object()
#         self.perform_destroy(group, **kwargs)
#         return Response(status=status.HTTP_204_NO_CONTENT)
#
#     def perform_destroy(self, instance, **kwargs):
#         user_id = kwargs.get('uid')
#         user = get_object_or_404(User, id=user_id)
#         instance.users.remove(user)
#
#
class UserAuthApi(APIView):
    permission_classes = ()
    expiration = settings.CONFIG.TOKEN_EXPIRATION or 3600

    def post(self, request, *args, **kwargs):
        username = request.data.get('username', '')
        password = request.data.get('password', '')
        public_key = request.data.get('public_key', '')
        remote_addr = request.data.get('remote_addr', '')
        terminal = request.data.get('terminal', '')
        login_type = request.data.get('login_type', 'T')
        user = check_user_valid(username=username, password=password, public_key=public_key)

        if user:
            token = cache.get('%s_%s' % (user.id, remote_addr))
            if not token:
                token = token_gen(user)

            cache.set(token, user.id, self.expiration)
            cache.set('%s_%s' % (user.id, remote_addr), token, self.expiration)
            write_login_log_async.delay(user.username, name=user.name, terminal=terminal,
                                        login_ip=remote_addr, login_type=login_type)
            return Response({'token': token, 'id': user.id, 'username': user.username, 'name': user.name})
        else:
            return Response({'msg': 'Invalid password or public key or user is not active or expired'}, status=401)
