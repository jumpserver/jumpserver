# ~*~ coding: utf-8 ~*~
#

import base64

from django.core.cache import cache
from django.conf import settings
from rest_framework import generics, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny
from rest_framework.authentication import SessionAuthentication
from rest_framework_bulk import BulkModelViewSet
from django_filters.rest_framework import DjangoFilterBackend

from common.mixins import IDInFilterMixin
from common.utils import get_logger
from .utils import check_user_valid, generate_token
from .models import User, UserGroup
from .hands import write_login_log_async
from .permissions import IsSuperUser, IsAppUser, IsValidUser, IsSuperUserOrAppUser
from . import serializers


logger = get_logger(__name__)


class UserViewSet(IDInFilterMixin, BulkModelViewSet):
    queryset = User.objects.all()
    serializer_class = serializers.UserSerializer
    permission_classes = (IsSuperUser,)
    filter_backends = (DjangoFilterBackend,)
    filter_fields = ('username', 'email', 'name', 'id')


class UserUpdateGroupApi(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = serializers.UserUpdateGroupSerializer
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


class UserGroupViewSet(IDInFilterMixin, BulkModelViewSet):
    queryset = UserGroup.objects.all()
    serializer_class = serializers.UserGroupSerializer


class UserGroupUpdateUserApi(generics.RetrieveUpdateAPIView):
    queryset = UserGroup.objects.all()
    serializer_class = serializers.UserGroupUpdateMemeberSerializer
    permission_classes = (IsSuperUser,)


class UserToken(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        username = request.data.get('username', '')
        email = request.data.get('email', '')
        password = request.data.get('password', '')
        public_key = request.data.get('public_key', '')

        user, msg = check_user_valid(username=username, email=email,
                                     password=password, public_key=public_key)
        if user:
            token = generate_token(request)
            return Response({'Token': token, 'key': 'Bearer'}, status=200)
        else:
            return Response({'error': msg}, status=406)


class UserProfile(APIView):
    permission_classes = (IsValidUser,)

    def get(self, request):
        return Response(request.user.to_json())


class UserAuthApi(APIView):
    permission_classes = ()
    expiration = settings.CONFIG.TOKEN_EXPIRATION or 3600

    def post(self, request, *args, **kwargs):
        username = request.data.get('username', '')
        password = request.data.get('password', '')
        public_key = request.data.get('public_key', '')
        remote_addr = request.data.get('remote_addr', '')
        terminal = request.data.get('applications', '')
        login_type = request.data.get('login_type', 'T')
        user = check_user_valid(username=username, password=password, public_key=public_key)

        if user:
            token = cache.get('%s_%s' % (user.id, remote_addr))
            if not token:
                token = generate_token(request)

            cache.set(token, user.id, self.expiration)
            cache.set('%s_%s' % (user.id, remote_addr), token, self.expiration)
            write_login_log_async.delay(user.username, name=user.name, terminal=terminal,
                                        login_ip=remote_addr, login_type=login_type)
            return Response({'token': token, 'id': user.id, 'username': user.username,
                             'name': user.name, 'is_active': user.is_active})
        else:
            return Response({'msg': 'Invalid password or public key or user is not active or expired'}, status=401)
