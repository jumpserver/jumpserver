from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import logout as auth_logout
from django.db.utils import IntegrityError
from django.http.request import HttpRequest
from django.http.response import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.views import View
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny, IsAuthenticated

from authentication import errors
from authentication.const import ConfirmType
from authentication.mixins import AuthMixin
from authentication.notifications import OAuthBindMessage
from authentication.permissions import UserConfirmation
from common.sdk.im.dingtalk import URL, DingTalk
from common.utils import get_logger
from common.utils.common import get_request_ip
from common.utils.django import get_object_or_none, reverse, safe_next_url
from common.utils.random import random_string
from common.views.mixins import PermissionsMixin, UserConfirmRequiredExceptionMixin
from users.models import User
from users.views import UserVerifyPasswordView
from .base import BaseLoginCallbackView
from .mixins import METAMixin, FlashMessageMixin

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
        state = self.request.GET.get('state')
        session_state = self.request.session.get(DINGTALK_STATE_SESSION_KEY)
        if state != session_state:
            return False
        return True

    def get_verify_state_failed_response(self, redirect_uri):
        msg = _("The system configuration is incorrect. Please contact your administrator")
        return self.get_failed_response(redirect_uri, msg, msg)

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
        user = request.user
        redirect_url = request.GET.get('redirect_url')

        redirect_uri = reverse('authentication:dingtalk-qr-bind-callback', kwargs={'user_id': user.id}, external=True)
        redirect_uri += '?' + urlencode({'redirect_url': redirect_url})

        url = self.get_qr_url(redirect_uri)
        return HttpResponseRedirect(url)


class DingTalkQRBindCallbackView(DingTalkQRMixin, View):
    permission_classes = (IsAuthenticated,)

    def get(self, request: HttpRequest, user_id):
        code = request.GET.get('code')
        redirect_url = request.GET.get('redirect_url')

        if not self.verify_state():
            return self.get_verify_state_failed_response(redirect_url)

        user = get_object_or_none(User, id=user_id)
        if user is None:
            logger.error(f'DingTalkQR bind callback error, user_id invalid: user_id={user_id}')
            msg = _('Invalid user_id')
            response = self.get_failed_response(redirect_url, msg, msg)
            return response

        if user.dingtalk_id:
            response = self.get_already_bound_response(redirect_url)
            return response

        dingtalk = DingTalk(
            appid=settings.DINGTALK_APPKEY,
            appsecret=settings.DINGTALK_APPSECRET,
            agentid=settings.DINGTALK_AGENTID
        )
        userid, __ = dingtalk.get_user_id_by_code(code)

        if not userid:
            msg = _('DingTalk query user failed')
            response = self.get_failed_response(redirect_url, msg, msg)
            return response

        try:
            user.dingtalk_id = userid
            user.save()
        except IntegrityError as e:
            if e.args[0] == 1062:
                msg = _('The DingTalk is already bound to another user')
                response = self.get_failed_response(redirect_url, msg, msg)
                return response
            raise e

        ip = get_request_ip(request)
        OAuthBindMessage(user, ip, _('DingTalk'), user_id).publish_async()
        msg = _('Binding DingTalk successfully')
        auth_logout(request)
        response = self.get_success_response(redirect_url, msg, msg)
        return response


class DingTalkEnableStartView(UserVerifyPasswordView):

    def get_success_url(self):
        referer = self.request.META.get('HTTP_REFERER')
        redirect_url = self.request.GET.get("redirect_url")

        success_url = reverse('authentication:dingtalk-qr-bind')

        success_url += '?' + urlencode({
            'redirect_url': redirect_url or referer
        })

        return success_url


class DingTalkQRLoginView(DingTalkQRMixin, METAMixin, View):
    permission_classes = (AllowAny,)

    def get(self, request: HttpRequest):
        redirect_url = request.GET.get('redirect_url') or reverse('index')
        next_url = self.get_next_url_from_meta() or reverse('index')
        next_url = safe_next_url(next_url, request=request)

        redirect_uri = reverse('authentication:dingtalk-qr-login-callback', external=True)
        redirect_uri += '?' + urlencode({
            'redirect_url': redirect_url,
            'next': next_url,
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

    def get(self, request: HttpRequest):
        redirect_url = request.GET.get('redirect_url')

        redirect_uri = reverse('authentication:dingtalk-oauth-login-callback', external=True)
        redirect_uri += '?' + urlencode({'redirect_url': redirect_url})

        url = self.get_oauth_url(redirect_uri)
        return HttpResponseRedirect(url)


class DingTalkOAuthLoginCallbackView(AuthMixin, DingTalkOAuthMixin, View):
    permission_classes = (AllowAny,)

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
        userid, __ = dingtalk.get_user_id_by_code(code)
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
