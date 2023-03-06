from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string
from django.core.cache import cache
from django.shortcuts import reverse
from django.http import Http404
from django.conf import settings

from common.utils.verify_code import SendAndVerifyCodeUtil
from common.permissions import IsValidUser
from common.utils.random import random_string
from common.utils import get_object_or_none
from authentication.serializers import (
    PasswordVerifySerializer, ResetPasswordCodeSerializer,
    ForgetPasswordPreviewingSerializer, ForgetPasswordAuthSerializer
)
from notifications.backends import client_name_mapper
from settings.utils import get_login_title
from users.models import User
from authentication.mixins import authenticate
from authentication.errors import PasswordInvalid
from authentication.mixins import AuthMixin


class UserResetPasswordSendCodeApi(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ResetPasswordCodeSerializer

    @staticmethod
    def is_valid_user(**kwargs):
        user = get_object_or_none(User, **kwargs)
        if not user:
            err_msg = _('User does not exist: {}').format(_("No user matched"))
            return None, err_msg
        if not user.is_local:
            err_msg = _(
                'The user is from {}, please go to the corresponding system to change the password'
            ).format(user.get_source_display())
            return None, err_msg
        return user, None

    def create(self, request, *args, **kwargs):
        token = request.GET.get('token')
        userinfo = cache.get(token)
        if not userinfo:
            return reverse('authentication:forgot-previewing')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        username = userinfo.get('username')
        form_type = serializer.validated_data['form_type']
        code = random_string(6, lower=False, upper=False)
        other_args = {}

        target = serializer.validated_data[form_type]
        query_key = 'phone' if form_type == 'sms' else form_type
        user, err = self.is_valid_user(username=username, **{query_key: target})
        if not user:
            return Response({'error': err}, status=400)

        subject = '%s: %s' % (get_login_title(), _('Forgot password'))
        context = {
            'user': user, 'title': subject, 'code': code,
        }
        message = render_to_string('authentication/_msg_reset_password_code.html', context)
        other_args['subject'], other_args['message'] = subject, message
        SendAndVerifyCodeUtil(target, code, backend=form_type, **other_args).gen_and_send_async()
        return Response({'data': 'ok'}, status=200)


class UserPasswordVerifyApi(AuthMixin, CreateAPIView):
    permission_classes = (IsValidUser,)
    serializer_class = PasswordVerifySerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data['password']
        user = self.request.user

        user = authenticate(request=request, username=user.username, password=password)
        if not user:
            raise PasswordInvalid

        self.mark_password_ok(user)
        return Response()


class ForgetPasswordPreviewingApi(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ForgetPasswordPreviewingSerializer


class ForgetPasswordAuthApi(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ForgetPasswordAuthSerializer

    def pre_check(self):
        token = self.request.query_params.get('token')
        if not token:
            raise Http404()
        user_info = cache.get(token)
        if not user_info:
            raise Http404()
        return user_info

    @staticmethod
    def get_backends(active_backends):
        backends = [
            {
                'name': _('Email'), 'is_active': True, 'value': 'email',
                'help_text': _('Input your email account, that will send a email to your')
            }
        ]
        for b in backends:
            if b['value'] not in active_backends:
                b['is_active'] = False

        if settings.XPACK_ENABLED:
            if settings.SMS_ENABLED:
                is_active = True
            else:
                is_active = False
            sms_backend = {
                'name': _('SMS'), 'is_active': is_active, 'value': 'sms',
                'help_text': _(
                    'Enter your mobile number and a verification code will be sent to your phone'
                ),
            }
            backends.append(sms_backend)
        return backends

    def get(self, request, *args, **kwargs):
        user_info = self.pre_check()
        backends = self.get_backends(set(user_info['receive_backends']))
        return Response(backends)

    def perform_create(self, serializer):
        self.pre_check()
