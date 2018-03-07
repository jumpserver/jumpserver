# ~*~ coding: utf-8 ~*~
import uuid

from django.core.cache import cache

from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_bulk import BulkModelViewSet

from .serializers import UserSerializer, UserGroupSerializer, \
    UserGroupUpdateMemeberSerializer, UserPKUpdateSerializer, \
    UserUpdateGroupSerializer, ChangeUserPasswordSerializer
from .tasks import write_login_log_async
from .models import User, UserGroup
from .permissions import IsSuperUser, IsValidUser, IsCurrentUserOrReadOnly, \
    IsSuperUserOrAppUser
from .utils import check_user_valid, generate_token
from common.mixins import IDInFilterMixin
from common.utils import get_logger


logger = get_logger(__name__)


class UserViewSet(IDInFilterMixin, BulkModelViewSet):
    queryset = User.objects.exclude(role="App")
    # queryset = User.objects.all().exclude(role="App").order_by("date_joined")
    serializer_class = UserSerializer
    permission_classes = (IsSuperUser, IsAuthenticated)
    filter_fields = ('username', 'email', 'name', 'id')


class ChangeUserPasswordApi(generics.RetrieveUpdateAPIView):
    permission_classes = (IsSuperUser,)
    queryset = User.objects.all()
    serializer_class = ChangeUserPasswordSerializer

    def perform_update(self, serializer):
        user = self.get_object()
        user.password_raw = serializer.validated_data["password"]
        user.save()


class UserUpdateGroupApi(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserUpdateGroupSerializer
    permission_classes = (IsSuperUser,)


class UserResetPasswordApi(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

    def perform_update(self, serializer):
        # Note: we are not updating the user object here.
        # We just do the reset-password stuff.
        import uuid
        from .utils import send_reset_password_mail
        user = self.get_object()
        user.password_raw = str(uuid.uuid4())
        user.save()
        send_reset_password_mail(user)


class UserResetPKApi(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def perform_update(self, serializer):
        from .utils import send_reset_ssh_key_mail
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


class UserGroupViewSet(IDInFilterMixin, BulkModelViewSet):
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer


class UserGroupUpdateUserApi(generics.RetrieveUpdateAPIView):
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupUpdateMemeberSerializer
    permission_classes = (IsSuperUser,)


class UserToken(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        if not request.user.is_authenticated:
            username = request.data.get('username', '')
            email = request.data.get('email', '')
            password = request.data.get('password', '')
            public_key = request.data.get('public_key', '')

            user, msg = check_user_valid(
                username=username, email=email,
                password=password, public_key=public_key)
        else:
            user = request.user
            msg = None
        if user:
            token = generate_token(request, user)
            return Response({'Token': token, 'Keyword': 'Bearer'}, status=200)
        else:
            return Response({'error': msg}, status=406)


class UserProfile(APIView):
    permission_classes = (IsValidUser,)

    def get(self, request):
        return Response(request.user.to_json())

    def post(self, request):
        return Response(request.user.to_json())


class UserAuthApi(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        username = request.data.get('username', '')
        password = request.data.get('password', '')
        public_key = request.data.get('public_key', '')
        login_type = request.data.get('login_type', '')
        login_ip = request.data.get('remote_addr', None)
        user_agent = request.data.get('HTTP_USER_AGENT', '')

        if not login_ip:
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')

            if x_forwarded_for and x_forwarded_for[0]:
                login_ip = x_forwarded_for[0]
            else:
                login_ip = request.META.get("REMOTE_ADDR")

        user, msg = check_user_valid(
            username=username, password=password,
            public_key=public_key
        )

        if user:
            token = generate_token(request, user)
            write_login_log_async.delay(
                user.username, ip=login_ip,
                type=login_type, user_agent=user_agent,
            )
            return Response({'token': token, 'user': user.to_json()})
        else:
            return Response({'msg': msg}, status=401)


class UserConnectionTokenApi(APIView):
    permission_classes = (IsSuperUserOrAppUser,)

    def post(self, request):
        user_id = request.data.get('user', '')
        asset_id = request.data.get('asset', '')
        system_user_id = request.data.get('system_user', '')
        token = str(uuid.uuid4())
        value = {
            'user': user_id,
            'asset': asset_id,
            'system_user': system_user_id
        }
        cache.set(token, value, timeout=3600)
        return Response({"token": token}, status=201)

    def get(self, request):
        token = request.query_params.get('token')
        value = cache.get(token, None)
        if value:
            cache.delete(token)
        return Response(value)



