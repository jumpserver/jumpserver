# ~*~ coding: utf-8 ~*~
import uuid

from django.core.cache import cache
from django.urls import reverse
from django.utils.translation import ugettext as _

from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_bulk import BulkModelViewSet

from .serializers import UserSerializer, UserGroupSerializer, \
    UserGroupUpdateMemeberSerializer, UserPKUpdateSerializer, \
    UserUpdateGroupSerializer, ChangeUserPasswordSerializer
from .tasks import write_login_log_async
from .models import User, UserGroup, LoginLog
from .permissions import IsSuperUser, IsValidUser, IsCurrentUserOrReadOnly, \
    IsSuperUserOrAppUser
from .utils import check_user_valid, generate_token, get_login_ip, \
    check_otp_code, set_user_login_failed_count_to_cache, is_block_login
from common.mixins import IDInFilterMixin
from common.utils import get_logger


logger = get_logger(__name__)


class UserViewSet(IDInFilterMixin, BulkModelViewSet):
    queryset = User.objects.exclude(role="App")
    serializer_class = UserSerializer
    permission_classes = (IsSuperUser,)
    filter_fields = ('username', 'email', 'name', 'id')

    def get_permissions(self):
        if self.action == "retrieve":
            self.permission_classes = (IsSuperUserOrAppUser,)
        return super().get_permissions()


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
        from .utils import send_reset_password_mail
        user = self.get_object()
        user.password_raw = str(uuid.uuid4())
        user.save()
        send_reset_password_mail(user)


class UserResetPKApi(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsAuthenticated,)

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


class UserUnblockPKApi(generics.UpdateAPIView):
    queryset = User.objects.all()
    permission_classes = (IsSuperUser,)
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


class UserGroupViewSet(IDInFilterMixin, BulkModelViewSet):
    queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer
    permission_classes = (IsSuperUser,)


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


class UserProfile(generics.RetrieveAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class UserOtpAuthApi(APIView):
    permission_classes = (AllowAny,)
    serializer_class = UserSerializer

    def post(self, request):
        otp_code = request.data.get('otp_code', '')
        seed = request.data.get('seed', '')

        user = cache.get(seed, None)
        if not user:
            return Response({'msg': '请先进行用户名和密码验证'}, status=401)

        if not check_otp_code(user.otp_secret_key, otp_code):
            data = {
                'username': user.username,
                'mfa': int(user.otp_enabled),
                'reason': LoginLog.REASON_MFA,
                'status': False
            }
            self.write_login_log(request, data)
            return Response({'msg': 'MFA认证失败'}, status=401)

        data = {
            'username': user.username,
            'mfa': int(user.otp_enabled),
            'reason': LoginLog.REASON_NOTHING,
            'status': True
        }
        self.write_login_log(request, data)
        token = generate_token(request, user)
        return Response(
            {
                'token': token,
                'user': self.serializer_class(user).data
             }
        )

    @staticmethod
    def write_login_log(request, data):
        login_ip = request.data.get('remote_addr', None)
        login_type = request.data.get('login_type', '')
        user_agent = request.data.get('HTTP_USER_AGENT', '')

        if not login_ip:
            login_ip = get_login_ip(request)

        tmp_data = {
            'ip': login_ip,
            'type': login_type,
            'user_agent': user_agent
        }
        data.update(tmp_data)
        write_login_log_async.delay(**data)


class UserAuthApi(APIView):
    permission_classes = (AllowAny,)
    serializer_class = UserSerializer
    key_prefix_limit = "_LOGIN_LIMIT_{}_{}"
    key_prefix_block = "_LOGIN_BLOCK_{}"

    def post(self, request):
        # limit login
        username = request.data.get('username')
        ip = request.data.get('remote_addr', None)
        ip = ip if ip else get_login_ip(request)
        key_limit = self.key_prefix_limit.format(username, ip)
        key_block = self.key_prefix_block.format(username)
        if is_block_login(key_limit):
            msg = _("Log in frequently and try again later")
            return Response({'msg': msg}, status=401)

        user, msg = self.check_user_valid(request)
        if not user:
            data = {
                'username': request.data.get('username', ''),
                'mfa': LoginLog.MFA_UNKNOWN,
                'reason': LoginLog.REASON_PASSWORD,
                'status': False
            }
            self.write_login_log(request, data)

            set_user_login_failed_count_to_cache(key_limit, key_block)
            return Response({'msg': msg}, status=401)

        if not user.otp_enabled:
            data = {
                'username': user.username,
                'mfa': int(user.otp_enabled),
                'reason': LoginLog.REASON_NOTHING,
                'status': True
            }
            self.write_login_log(request, data)
            token = generate_token(request, user)
            return Response(
                {
                    'token': token,
                    'user': self.serializer_class(user).data
                }
            )

        seed = uuid.uuid4().hex
        cache.set(seed, user, 300)
        return Response(
            {
                'code': 101,
                'msg': '请携带seed值,进行MFA二次认证',
                'otp_url': reverse('api-users:user-otp-auth'),
                'seed': seed,
                'user': self.serializer_class(user).data
            }, status=300
        )

    @staticmethod
    def check_user_valid(request):
        username = request.data.get('username', '')
        password = request.data.get('password', '')
        public_key = request.data.get('public_key', '')
        user, msg = check_user_valid(
            username=username, password=password,
            public_key=public_key
        )
        return user, msg

    @staticmethod
    def write_login_log(request, data):
        login_ip = request.data.get('remote_addr', None)
        login_type = request.data.get('login_type', '')
        user_agent = request.data.get('HTTP_USER_AGENT', '')

        if not login_ip:
            login_ip = get_login_ip(request)

        tmp_data = {
            'ip': login_ip,
            'type': login_type,
            'user_agent': user_agent,
        }
        data.update(tmp_data)

        write_login_log_async.delay(**data)


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
        cache.set(token, value, timeout=20)
        return Response({"token": token}, status=201)

    def get(self, request):
        token = request.query_params.get('token')
        user_only = request.query_params.get('user-only', None)
        value = cache.get(token, None)

        if not value:
            return Response('', status=404)

        if not user_only:
            return Response(value)
        else:
            return Response({'user': value['user']})

    def get_permissions(self):
        if self.request.query_params.get('user-only', None):
            self.permission_classes = (AllowAny,)
        return super().get_permissions()
