# ~*~ coding: utf-8 ~*~
#

import logging

from django.shortcuts import get_object_or_404

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework_bulk import ListBulkCreateUpdateDestroyAPIView

from .serializers import UserSerializer, UserGroupSerializer, UserAttributeSerializer, UserGroupEditSerializer, \
    GroupEditSerializer, UserPKUpdateSerializer, UserBulkUpdateSerializer
from .models import User, UserGroup


logger = logging.getLogger('jumpserver.users.api')


class UserListAddApi(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserDetailDeleteUpdateApi(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def delete(self, request, *args, **kwargs):
        print(self.request.data)
        return super(UserDetailDeleteUpdateApi, self).delete(request, *args, **kwargs)


class UserGroupListAddApi(generics.ListCreateAPIView):
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer


class UserGroupDetailDeleteUpdateApi(generics.RetrieveUpdateDestroyAPIView):
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer


class UserAttributeApi(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserAttributeSerializer


class UserGroupEditApi(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserGroupEditSerializer


class UserResetPasswordApi(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserGroupEditSerializer

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
    serializer_class = UserGroupEditSerializer

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


class GroupDeleteApi(generics.DestroyAPIView):
    queryset = UserGroup.objects.all()
    serializer_class = GroupEditSerializer


class UserBulkUpdateApi(ListBulkCreateUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserBulkUpdateSerializer

    def filter_queryset(self, queryset):
        id_list = self.request.query_params.get('id__in')
        if id_list:
            import json
            try:
                ids = json.loads(id_list)
            except Exception as e:
                logger.error(str(e))
                return queryset
            if isinstance(ids, list):
                queryset = queryset.filter(id__in=ids)
        return queryset


class DeleteUserFromGroupApi(generics.DestroyAPIView):
    queryset = UserGroup.objects.all()
    serializer_class = GroupEditSerializer

    def destroy(self, request, *args, **kwargs):
        group = self.get_object()
        self.perform_destroy(group, **kwargs)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance, **kwargs):
        user_id = kwargs.get('uid')
        user = get_object_or_404(User, id=user_id)
        instance.users.remove(user)
