import time

from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.shortcuts import reverse
from django.template.loader import render_to_string
from django.utils.translation import gettext as _
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from authentication.errors import PasswordInvalid, IntervalTooShort
from authentication.mixins import AuthMixin
from authentication.mixins import authenticate
from authentication.serializers import (
    PasswordVerifySerializer, ResetPasswordCodeSerializer
)
from authentication.utils import check_user_property_is_correct
from common.permissions import IsValidUser
from common.utils.random import random_string
from common.utils.verify_code import SendAndVerifyCodeUtil
from settings.utils import get_login_title


class UserResetPasswordSendCodeApi(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ResetPasswordCodeSerializer

    @staticmethod
    def is_valid_user(username, **properties):
        user = check_user_property_is_correct(username, **properties)
        if not user:
            err_msg = _('User does not exist: {}').format(_("No user matched"))
            return None, err_msg
        if not user.is_local:
            err_msg = _(
                'The user is from {}, please go to the corresponding system to change the password'
            ).format(user.get_source_display())
            return None, err_msg
        return user, None

    @staticmethod
    def safe_send_code(token, code, target, form_type, content):
        token_sent_key = '{}_send_at'.format(token)
        token_send_at = cache.get(token_sent_key, 0)
        if token_send_at:
            raise IntervalTooShort(60)
        SendAndVerifyCodeUtil(target, code, backend=form_type, **content).gen_and_send_async()
        cache.set(token_sent_key, int(time.time()), 60)

    def prepare_code_data(self, user_info, serializer):
        username = user_info.get('username')
        form_type = serializer.validated_data['form_type']

        target = serializer.validated_data[form_type]
        if form_type == 'sms':
            query_key = 'phone'
        else:
            query_key = form_type
        user, err = self.is_valid_user(username=username, **{query_key: target})
        if not user:
            raise ValueError(err)

        code = random_string(6, lower=False, upper=False)
        subject = '%s: %s' % (get_login_title(), _('Forgot password'))
        context = {
            'user': user, 'title': subject, 'code': code,
        }
        message = render_to_string('authentication/_msg_reset_password_code.html', context)
        content = {'subject': subject, 'message': message}
        return code, target, form_type, content

    def create(self, request, *args, **kwargs):
        token = request.GET.get('token')
        user_info = cache.get(token)
        if not user_info:
            return HttpResponseRedirect(reverse('authentication:forgot-previewing'))

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            code, target, form_type, content = self.prepare_code_data(user_info, serializer)
        except ValueError as e:
            return Response({'error': str(e)}, status=400)
        self.safe_send_code(token, code, target, form_type, content)
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
