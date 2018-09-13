# -*- coding: utf-8 -*-
#
import uuid

from django.core.cache import cache
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _

from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utils import get_logger, get_request_ip
from common.permissions import IsOrgAdminOrAppUser
from orgs.mixins import RootOrgViewMixin
from ..serializers import UserSerializer
from ..tasks import write_login_log_async
from ..models import User, LoginLog
from ..utils import check_user_valid, generate_token, \
    check_otp_code, increase_login_failed_count, is_block_login, \
    clean_failed_count
from ..hands import Asset, SystemUser


logger = get_logger(__name__)


class UserAuthApi(RootOrgViewMixin, APIView):
    permission_classes = (AllowAny,)
    serializer_class = UserSerializer

    def post(self, request):
        # limit login
        username = request.data.get('username')
        ip = request.data.get('remote_addr', None)
        ip = ip or get_request_ip(request)

        if is_block_login(username, ip):
            msg = _("Log in frequently and try again later")
            logger.warn(msg + ': ' + username + ':' + ip)
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
            increase_login_failed_count(username, ip)
            return Response({'msg': msg}, status=401)

        if not user.otp_enabled:
            data = {
                'username': user.username,
                'mfa': int(user.otp_enabled),
                'reason': LoginLog.REASON_NOTHING,
                'status': True
            }
            self.write_login_log(request, data)
            # 登陆成功，清除原来的缓存计数
            clean_failed_count(username, ip)
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
                'msg': _('Please carry seed value and '
                         'conduct MFA secondary certification'),
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
            login_ip = get_request_ip(request)

        tmp_data = {
            'ip': login_ip,
            'type': login_type,
            'user_agent': user_agent,
        }
        data.update(tmp_data)

        write_login_log_async.delay(**data)


class UserConnectionTokenApi(RootOrgViewMixin, APIView):
    permission_classes = (IsOrgAdminOrAppUser,)

    def post(self, request):
        user_id = request.data.get('user', '')
        asset_id = request.data.get('asset', '')
        system_user_id = request.data.get('system_user', '')
        token = str(uuid.uuid4())
        user = get_object_or_404(User, id=user_id)
        asset = get_object_or_404(Asset, id=asset_id)
        system_user = get_object_or_404(SystemUser, id=system_user_id)
        value = {
            'user': user_id,
            'username': user.username,
            'asset': asset_id,
            'hostname': asset.hostname,
            'system_user': system_user_id,
            'system_user_name': system_user.name
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


class UserOtpAuthApi(RootOrgViewMixin, APIView):
    permission_classes = (AllowAny,)
    serializer_class = UserSerializer

    def post(self, request):
        otp_code = request.data.get('otp_code', '')
        seed = request.data.get('seed', '')

        user = cache.get(seed, None)
        if not user:
            return Response(
                {'msg': _('Please verify the user name and password first')},
                status=401
            )

        if not check_otp_code(user.otp_secret_key, otp_code):
            data = {
                'username': user.username,
                'mfa': int(user.otp_enabled),
                'reason': LoginLog.REASON_MFA,
                'status': False
            }
            self.write_login_log(request, data)
            return Response({'msg': _('MFA certification failed')}, status=401)

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
            login_ip = get_request_ip(request)

        tmp_data = {
            'ip': login_ip,
            'type': login_type,
            'user_agent': user_agent
        }
        data.update(tmp_data)
        write_login_log_async.delay(**data)
