from rest_framework.generics import CreateAPIView, GenericAPIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string
from django.core.cache import cache
from django.http import Http404
from django.conf import settings
from django.db import IntegrityError

from common.utils.verify_code import SendAndVerifyCodeUtil
from common.permissions import IsValidUser
from common.utils.random import random_string
from common.utils import get_object_or_none, FlashMessageUtil, reverse
from authentication.serializers import (
    PasswordVerifySerializer, ResetPasswordCodeSerializer,
    ForgetPasswordPreviewingSerializer, ForgetPasswordAuthSerializer,
    LoginSerializer, LoginCaptchaSerializer, ResetPasswordSerializer
)
from settings.utils import get_login_title
from users.models import User
from users.mixins import UserLoginContextMixin
from users.utils import check_password_rules
from users.notifications import ResetPasswordSuccessMsg
from authentication.mixins import authenticate, AuthMixin
from authentication.const import RSA_PUBLIC_KEY, RSA_PRIVATE_KEY
from authentication import errors


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
            raise errors.PasswordInvalid

        self.mark_password_ok(user)
        return Response()


class ForgetPasswordPreviewingApi(CreateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ForgetPasswordPreviewingSerializer


class UserForgotPasswordApi(GenericAPIView):
    permission_classes = (AllowAny,)


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


class UserResetPasswordApi(GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = ResetPasswordSerializer

    @staticmethod
    def get_redirect_url(action, msg):
        action_mapping = {
            'success': (_('Reset password success'), 'message'),
            'invalid': (_('Reset password'), 'error'),
            'cannot_update': (_('Reset password'), 'error'),
        }
        title, msg_type = action_mapping[action]
        message_data = {'title': title, 'redirect_url': reverse('api-auth:login'), msg_type: msg}
        return FlashMessageUtil.gen_message_url(message_data)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        token = self.request.GET.get('token')
        user = User.validate_reset_password_token(token)
        if not user:
            error = _('Token invalid or expired')
            url = self.get_redirect_url('invalid', error)
            return Response({'redirect': url}, status=200)

        if not user.can_update_password():
            error = _('User auth from {}, go there change password').format(user.get_source_display())
            url = self.get_redirect_url('cannot_update', error)
            return Response({'redirect': url}, status=200)

        password = serializer.validated_data['new_password']
        is_ok = check_password_rules(password, is_org_admin=user.is_org_admin)
        if not is_ok:
            error = _('* Your password does not meet the requirements')
            return Response({'new_password': error}, status=400)

        if user.is_history_password(password):
            limit_count = settings.OLD_PASSWORD_HISTORY_LIMIT_COUNT
            error = _('* The new password cannot be the last {} passwords').format(
                limit_count
            )
            return Response({'new_password': error}, status=400)

        user.reset_password(password)
        User.expired_reset_password_token(token)

        ResetPasswordSuccessMsg(user, self.request).publish_async()
        msg = _('Reset password success, return to login page')
        return Response({'redirect': self.get_redirect_url('success', msg)})


class LoginApi(AuthMixin, UserLoginContextMixin, GenericAPIView):
    permission_classes = (AllowAny,)

    def get_serializer_class(self):
        serializer_class = LoginSerializer
        if self.check_is_need_captcha():
            serializer_class = LoginCaptchaSerializer
        return serializer_class

    def redirect_third_party_auth_if_need(self, request):
        # show jumpserver login page if request http://{JUMP-SERVER}/?admin=1
        if self.request.GET.get("admin", 0):
            return None

        auth_types = [m for m in self.get_support_auth_methods() if m.get('auto_redirect')]
        if not auth_types:
            return None

        # 明确直接登录哪个
        login_to = settings.LOGIN_REDIRECT_TO_BACKEND.upper()
        if login_to == 'DIRECT':
            return None

        auth_method = next(filter(lambda x: x['name'] == login_to, auth_types), None)
        if not auth_method:
            auth_method = auth_types[0]

        auth_name, redirect_url = auth_method['name'], auth_method['url']
        next_url = request.GET.get('next') or '/'
        query_string = request.GET.urlencode()
        redirect_url = '{}?next={}&{}'.format(redirect_url, next_url, query_string)

        if settings.LOGIN_REDIRECT_MSG_ENABLED:
            message_data = {
                'title': _('Redirecting'),
                'message': _("Redirecting to {} authentication").format(auth_name),
                'redirect_url': redirect_url,
                'interval': 3,
                'has_cancel': True,
                'cancel_url': reverse('api-auth:login', api_to_ui=True) + '?admin=1'
            }
            redirect_url = FlashMessageUtil.gen_message_url(message_data)
        return redirect_url

    def clear_rsa_key(self):
        self.request.session[RSA_PRIVATE_KEY] = None
        self.request.session[RSA_PUBLIC_KEY] = None

    def get(self, request, *args, **kwargs):
        # if request.user.is_staff:
        #     first_login_url = redirect_user_first_login_or_index(
        #         request, REDIRECT_FIELD_NAME
        #     )
        #     return Response(data={'redirect': first_login_url}, status=200)
        redirect_url = self.redirect_third_party_auth_if_need(request)
        if redirect_url:
            return Response(data={'redirect': redirect_url}, status=200)
        request.session.set_test_cookie()
        return Response(status=200)

    def post(self, request, *args, **kwargs):
        # if not self.request.session.test_cookie_worked():
        #     return Response({'error': _("Please enable cookies and try again.")}, status=400)
        # https://docs.djangoproject.com/en/3.1/topics/http/sessions/#setting-test-cookies
        # self.request.session.delete_test_cookie()

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        try:
            self.check_user_auth(serializer.validated_data)
        except errors.AuthFailedError as e:
            response = Response({'error': e.msg}, status=400)
            self.set_login_failed_mark()
            self.request.session.set_test_cookie()
            return response
        except errors.NeedRedirectError as e:
            return Response({'redirect': e.url}, status=200)
        except (
                errors.MFAFailedError,
                errors.BlockMFAError,
                errors.MFACodeRequiredError,
                errors.SMSCodeRequiredError,
                errors.UserPhoneNotSet,
                errors.BlockGlobalIpLoginError
        ) as e:
            return Response({'code': e.msg}, status=400)
        except (IntegrityError,) as e:
            # (1062, "Duplicate entry 'youtester001@example.com' for key 'users_user.email'")
            error = str(e)
            if len(e.args) < 2:
                return Response({'error': error}, status=400)

            msg_list = e.args[1].split("'")
            if len(msg_list) < 4:
                return Response({'error': error}, status=400)

            email, field = msg_list[1], msg_list[3]
            if field == 'users_user.email':
                error = _('User email already exists ({})').format(email)
            return Response({'error': error}, status=400)

        self.clear_rsa_key()
        return self.redirect_to_guard_view()
