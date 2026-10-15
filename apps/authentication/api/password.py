from django.utils.translation import get_language, gettext as _
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from authentication import errors, password_reset
from authentication.mixins import AuthMixin, authenticate
from authentication.serializers import PasswordVerifySerializer, ResetPasswordCodeSerializer
from authentication.tasks import send_password_reset_code
from common.permissions import IsValidUser
from common.utils import get_logger
from users.utils import LoginBlockUtil, LoginIpBlockUtil

logger = get_logger(__name__)


class UserResetPasswordSendCodeApi(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ResetPasswordCodeSerializer

    def create(self, request, *args, **kwargs):
        token = request.GET.get('token')
        flow = password_reset.get_flow(request, token)
        if not flow:
            return Response({
                'error': _('This page has expired. Please start again.'),
                'code': 'password_reset_expired',
            }, status=status.HTTP_400_BAD_REQUEST)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        form_type = serializer.validated_data['form_type']
        target = serializer.validated_data[form_type]
        try:
            request_id = password_reset.reserve_send(request, token, flow, form_type, target)
        except password_reset.RecoveryThrottled as exc:
            return Response({'error': str(exc), 'retry_after': exc.wait},
                            status=status.HTTP_429_TOO_MANY_REQUESTS,
                            headers={'Retry-After': str(exc.wait)})
        # Queue all well-formed requests, including unknown accounts. Account lookup
        # and delivery do not affect the public response or its processing time.
        try:
            send_password_reset_code.apply_async(
                args=(token, request_id, form_type, target, get_language()),
                argsrepr='(<redacted>)', priority=100,
            )
        except Exception:
            logger.error('Unable to enqueue password recovery request')
            return Response({'error': _('Service unavailable. Please try again later.')},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response({'data': 'ok', 'retry_after': password_reset.SEND_INTERVAL})


class UserPasswordVerifyApi(AuthMixin, CreateAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = PasswordVerifySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data['password']
        user = self.request.user
        request_username = serializer.validated_data.get('username') or user.username
        username = request_username
        ip = self.get_request_ip()
        self._set_partial_credential_error(username=username, ip=ip, request=request)

        try:
            self._check_is_block(username)
            user = authenticate(request=request, username=username, password=password)
            if not user:
                self.raise_credential_error(errors.reason_password_failed)
            if user.is_expired:
                self.raise_credential_error(errors.reason_user_expired)
            if not user.is_active:
                self.raise_credential_error(errors.reason_user_inactive)

            LoginBlockUtil(username, ip).clean_failed_count()
            LoginIpBlockUtil(ip).clean_block_if_need()
            return Response(status=status.HTTP_200_OK)
        except errors.AuthFailedError as e:
            data = e.as_data()
            if e.error in {'block_login', 'block_global_ip_login'}:
                return Response(data, status=status.HTTP_429_TOO_MANY_REQUESTS)
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
