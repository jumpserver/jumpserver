from urllib.parse import urlencode

from django.conf import settings
from django.http.request import HttpRequest
from django.http.response import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.views import View
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny, IsAuthenticated

from authentication import errors
from authentication.const import ConfirmType
from authentication.decorators import post_save_next_to_session_if_guard_redirect, pre_save_next_to_session
from authentication.mixins import AuthMixin
from authentication.permissions import UserConfirmation
from common.sdk.im.dingtalk import URL, DingTalk
from common.utils import get_logger
from common.utils.django import get_object_or_none, reverse
from common.utils.random import random_string
from common.views.mixins import PermissionsMixin, UserConfirmRequiredExceptionMixin
from users.models import User
from users.views import UserVerifyPasswordView
from .base import BaseBindCallbackView, BaseLoginCallbackView
from .mixins import FlashMessageMixin

logger = get_logger(__file__)

DINGTALK_STATE_SESSION_KEY = '_dingtalk_state'


class DingTalkBaseMixin(UserConfirmRequiredExceptionMixin, PermissionsMixin, FlashMessageMixin, View):
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except APIException as e:
            try:
                msg = e.detail['errmsg']
            except Exception:
                msg = _('DingTalk Error, Please contact your system administrator')
            return self.get_failed_response(
                '/',
                _('DingTalk Error'),
                msg
            )

    def verify_state(self):
        return self.verify_state_with_session_key(DINGTALK_STATE_SESSION_KEY)

    def get_already_bound_response(self, redirect_url):
        msg = _('DingTalk is already bound')
        response = self.get_failed_response(redirect_url, msg, msg)
        return response


class DingTalkQRMixin(DingTalkBaseMixin, View):

    def get_qr_url(self, redirect_uri):
        state = random_string(16)
        self.request.session[DINGTALK_STATE_SESSION_KEY] = state

        params = {
            'client_id': settings.DINGTALK_APPKEY,
            'response_type': 'code',
            'scope': 'openid',
            'state': state,
            'redirect_uri': redirect_uri,
            'prompt': 'consent'
        }
        url = URL.QR_CONNECT + '?' + urlencode(params)
        return url


class DingTalkOAuthMixin(DingTalkBaseMixin, View):

    def get_oauth_url(self, redirect_uri):
        if not settings.AUTH_DINGTALK:
            return reverse('authentication:login')
        state = random_string(16)
        self.request.session[DINGTALK_STATE_SESSION_KEY] = state

        params = {
            'appid': settings.DINGTALK_APPKEY,
            'response_type': 'code',
            'scope': 'snsapi_auth',
            'state': state,
            'redirect_uri': redirect_uri,
        }
        url = URL.OAUTH_CONNECT + '?' + urlencode(params)
        return url


class DingTalkQRBindView(DingTalkQRMixin, View):
    permission_classes = (IsAuthenticated, UserConfirmation.require(ConfirmType.RELOGIN))

    def get(self, request: HttpRequest):
        redirect_url = request.GET.get('redirect_url')

        redirect_uri = reverse('authentication:dingtalk-qr-bind-callback', external=True)
        redirect_uri += '?' + urlencode({'redirect_url': redirect_url})

        url = self.get_qr_url(redirect_uri)
        return HttpResponseRedirect(url)


class DingTalkQRBindCallbackView(DingTalkQRMixin, BaseBindCallbackView):
    permission_classes = (IsAuthenticated,)

    client_type_path = 'common.sdk.im.dingtalk.DingTalk'
    client_auth_params = {
        'appid': 'DINGTALK_APPKEY', 'appsecret': 'DINGTALK_APPSECRET',
        'agentid': 'DINGTALK_AGENTID'
    }
    auth_type = 'dingtalk'
    auth_type_label = _('DingTalk')


class DingTalkEnableStartView(UserVerifyPasswordView):

    def get_success_url(self):
        referer = self.request.META.get('HTTP_REFERER')
        redirect_url = self.request.GET.get("redirect_url")

        success_url = reverse('authentication:dingtalk-qr-bind')

        success_url += '?' + urlencode({
            'redirect_url': redirect_url or referer
        })

        return success_url


class DingTalkQRLoginView(DingTalkQRMixin, View):
    permission_classes = (AllowAny,)

    @pre_save_next_to_session()
    def get(self, request: HttpRequest):
        redirect_url = request.GET.get('redirect_url') or reverse('index')
        query_string = request.GET.urlencode()
        redirect_url = f'{redirect_url}?{query_string}'

        redirect_uri = reverse('authentication:dingtalk-qr-login-callback', external=True)
        redirect_uri += '?' + urlencode({
            'redirect_url': redirect_url,
        })

        url = self.get_qr_url(redirect_uri)
        return HttpResponseRedirect(url)


class DingTalkQRLoginCallbackView(DingTalkQRMixin, BaseLoginCallbackView):
    permission_classes = (AllowAny,)

    client_type_path = 'common.sdk.im.dingtalk.DingTalk'
    client_auth_params = {
        'appid': 'DINGTALK_APPKEY', 'appsecret': 'DINGTALK_APPSECRET',
        'agentid': 'DINGTALK_AGENTID'
    }
    user_type = 'dingtalk'
    auth_backend = 'AUTH_BACKEND_DINGTALK'

    msg_client_err = _('DingTalk Error')
    msg_user_not_bound_err = _('DingTalk is not bound')
    msg_not_found_user_from_client_err = _('Failed to get user from DingTalk')


class DingTalkOAuthLoginView(DingTalkOAuthMixin, View):
    permission_classes = (AllowAny,)

    @pre_save_next_to_session()
    def get(self, request: HttpRequest):
        redirect_url = request.GET.get('redirect_url')

        redirect_uri = reverse('authentication:dingtalk-oauth-login-callback', external=True)
        redirect_uri += '?' + urlencode({'redirect_url': redirect_url})

        url = self.get_oauth_url(redirect_uri)
        return HttpResponseRedirect(url)


class DingTalkOAuthLoginCallbackView(AuthMixin, DingTalkOAuthMixin, View):
    permission_classes = (AllowAny,)

    @post_save_next_to_session_if_guard_redirect
    def get(self, request: HttpRequest):
        code = request.GET.get('code')
        redirect_url = request.GET.get('redirect_url')
        login_url = reverse('authentication:login')

        if not self.verify_state():
            return self.get_verify_state_failed_response(redirect_url)

        dingtalk = DingTalk(
            appid=settings.DINGTALK_APPKEY,
            appsecret=settings.DINGTALK_APPSECRET,
            agentid=settings.DINGTALK_AGENTID
        )
        userid, __ = dingtalk.get_user_id_by_code_for_oauth(code)
        if not userid:
            # 正常流程不会出这个错误，hack 行为
            msg = _('Failed to get user from DingTalk')
            response = self.get_failed_response(login_url, title=msg, msg=msg)
            return response

        user = get_object_or_none(User, dingtalk_id=userid)
        if user is None:
            title = _('DingTalk is not bound')
            msg = _('Please login with a password and then bind the DingTalk')
            response = self.get_failed_response(login_url, title=title, msg=msg)
            return response

        try:
            self.check_oauth2_auth(user, settings.AUTH_BACKEND_DINGTALK)
        except errors.AuthFailedError as e:
            self.set_login_failed_mark()
            msg = e.msg
            response = self.get_failed_response(login_url, title=msg, msg=msg)
            return response

        return self.redirect_to_guard_view()
