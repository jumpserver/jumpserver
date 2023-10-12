from urllib.parse import urlencode

from django.conf import settings
from django.db.utils import IntegrityError
from django.http.request import HttpRequest
from django.http.response import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.views import View
from rest_framework.exceptions import APIException
from rest_framework.permissions import IsAuthenticated, AllowAny

from authentication import errors
from authentication.const import ConfirmType
from authentication.mixins import AuthMixin
from authentication.notifications import OAuthBindMessage
from authentication.permissions import UserConfirmation
from common.sdk.im.wecom import URL
from common.sdk.im.wecom import WeCom
from common.utils import get_logger
from common.utils.common import get_request_ip
from common.utils.django import reverse, get_object_or_none
from common.utils.random import random_string
from common.views.mixins import UserConfirmRequiredExceptionMixin, PermissionsMixin
from users.models import User
from users.views import UserVerifyPasswordView
from .base import BaseLoginCallbackView
from .mixins import METAMixin, FlashMessageMixin

logger = get_logger(__file__)

WECOM_STATE_SESSION_KEY = '_wecom_state'


class WeComBaseMixin(UserConfirmRequiredExceptionMixin, PermissionsMixin, FlashMessageMixin, View):
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except APIException as e:
            try:
                msg = e.detail['errmsg']
            except Exception:
                msg = _('WeCom Error, Please contact your system administrator')
            return self.get_failed_response(
                '/',
                _('WeCom Error'),
                msg
            )

    def verify_state(self):
        state = self.request.GET.get('state')
        session_state = self.request.session.get(WECOM_STATE_SESSION_KEY)
        if state != session_state:
            return False
        return True

    def get_verify_state_failed_response(self, redirect_uri):
        msg = _("The system configuration is incorrect. Please contact your administrator")
        return self.get_failed_response(redirect_uri, msg, msg)

    def get_already_bound_response(self, redirect_url):
        msg = _('WeCom is already bound')
        response = self.get_failed_response(redirect_url, msg, msg)
        return response


class WeComQRMixin(WeComBaseMixin, View):

    def get_qr_url(self, redirect_uri):
        state = random_string(16)
        self.request.session[WECOM_STATE_SESSION_KEY] = state

        params = {
            'appid': settings.WECOM_CORPID,
            'agentid': settings.WECOM_AGENTID,
            'state': state,
            'redirect_uri': redirect_uri,
        }
        url = URL.QR_CONNECT + '?' + urlencode(params)
        return url


class WeComOAuthMixin(WeComBaseMixin, View):

    def get_oauth_url(self, redirect_uri):
        if not settings.AUTH_WECOM:
            return reverse('authentication:login')
        state = random_string(16)
        self.request.session[WECOM_STATE_SESSION_KEY] = state

        params = {
            'appid': settings.WECOM_CORPID,
            'agentid': settings.WECOM_AGENTID,
            'state': state,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'snsapi_base',
        }
        url = URL.OAUTH_CONNECT + '?' + urlencode(params) + '#wechat_redirect'
        return url


class WeComQRBindView(WeComQRMixin, View):
    permission_classes = (IsAuthenticated, UserConfirmation.require(ConfirmType.RELOGIN))

    def get(self, request: HttpRequest):
        user = request.user
        redirect_url = request.GET.get('redirect_url')

        redirect_uri = reverse('authentication:wecom-qr-bind-callback', kwargs={'user_id': user.id}, external=True)
        redirect_uri += '?' + urlencode({'redirect_url': redirect_url})

        url = self.get_qr_url(redirect_uri)
        return HttpResponseRedirect(url)


class WeComQRBindCallbackView(WeComQRMixin, View):
    permission_classes = (IsAuthenticated,)

    def get(self, request: HttpRequest, user_id):
        code = request.GET.get('code')
        redirect_url = request.GET.get('redirect_url')

        if not self.verify_state():
            return self.get_verify_state_failed_response(redirect_url)

        user = get_object_or_none(User, id=user_id)
        if user is None:
            logger.error(f'WeComQR bind callback error, user_id invalid: user_id={user_id}')
            msg = _('Invalid user_id')
            response = self.get_failed_response(redirect_url, msg, msg)
            return response

        if user.wecom_id:
            response = self.get_already_bound_response(redirect_url)
            return response

        wecom = WeCom(
            corpid=settings.WECOM_CORPID,
            corpsecret=settings.WECOM_SECRET,
            agentid=settings.WECOM_AGENTID
        )
        wecom_userid, __ = wecom.get_user_id_by_code(code)
        if not wecom_userid:
            msg = _('WeCom query user failed')
            response = self.get_failed_response(redirect_url, msg, msg)
            return response

        try:
            user.wecom_id = wecom_userid
            user.save()
        except IntegrityError as e:
            if e.args[0] == 1062:
                msg = _('The WeCom is already bound to another user')
                response = self.get_failed_response(redirect_url, msg, msg)
                return response
            raise e

        ip = get_request_ip(request)
        OAuthBindMessage(user, ip, _('WeCom'), wecom_userid).publish_async()
        msg = _('Binding WeCom successfully')
        response = self.get_success_response(redirect_url, msg, msg)
        return response


class WeComEnableStartView(UserVerifyPasswordView):
    def get_success_url(self):
        referer = self.request.META.get('HTTP_REFERER')
        redirect_url = self.request.GET.get("redirect_url")

        success_url = reverse('authentication:wecom-qr-bind')
        success_url += '?' + urlencode({
            'redirect_url': redirect_url or referer
        })
        return success_url


class WeComQRLoginView(WeComQRMixin, METAMixin, View):
    permission_classes = (AllowAny,)

    def get(self, request: HttpRequest):
        redirect_url = request.GET.get('redirect_url') or reverse('index')
        next_url = self.get_next_url_from_meta() or reverse('index')
        redirect_uri = reverse('authentication:wecom-qr-login-callback', external=True)
        redirect_uri += '?' + urlencode({
            'redirect_url': redirect_url,
            'next': next_url,
        })

        url = self.get_qr_url(redirect_uri)
        return HttpResponseRedirect(url)


class WeComQRLoginCallbackView(WeComQRMixin, BaseLoginCallbackView):
    permission_classes = (AllowAny,)

    client_type_path = 'common.sdk.im.wecom.WeCom'
    client_auth_params = {'corpid': 'WECOM_CORPID', 'corpsecret': 'WECOM_SECRET', 'agentid': 'WECOM_AGENTID'}
    user_type = 'wecom'
    auth_backend = 'AUTH_BACKEND_WECOM'

    msg_client_err = _('WeCom Error')
    msg_user_not_bound_err = _('WeCom is not bound')
    msg_not_found_user_from_client_err = _('Failed to get user from WeCom')


class WeComOAuthLoginView(WeComOAuthMixin, View):
    permission_classes = (AllowAny,)

    def get(self, request: HttpRequest):
        redirect_url = request.GET.get('redirect_url')

        redirect_uri = reverse('authentication:wecom-oauth-login-callback', external=True)
        redirect_uri += '?' + urlencode({'redirect_url': redirect_url})

        url = self.get_oauth_url(redirect_uri)
        return HttpResponseRedirect(url)


class WeComOAuthLoginCallbackView(AuthMixin, WeComOAuthMixin, View):
    permission_classes = (AllowAny,)

    def get(self, request: HttpRequest):
        code = request.GET.get('code')
        redirect_url = request.GET.get('redirect_url')
        login_url = reverse('authentication:login')

        if not self.verify_state():
            return self.get_verify_state_failed_response(redirect_url)

        wecom = WeCom(
            corpid=settings.WECOM_CORPID,
            corpsecret=settings.WECOM_SECRET,
            agentid=settings.WECOM_AGENTID
        )
        wecom_userid, __ = wecom.get_user_id_by_code(code)
        if not wecom_userid:
            # 正常流程不会出这个错误，hack 行为
            msg = _('Failed to get user from WeCom')
            response = self.get_failed_response(login_url, title=msg, msg=msg)
            return response

        user = get_object_or_none(User, wecom_id=wecom_userid)
        if user is None:
            title = _('WeCom is not bound')
            msg = _('Please login with a password and then bind the WeCom')
            response = self.get_failed_response(login_url, title=title, msg=msg)
            return response

        try:
            self.check_oauth2_auth(user, settings.AUTH_BACKEND_WECOM)
        except errors.AuthFailedError as e:
            self.set_login_failed_mark()
            msg = e.msg
            response = self.get_failed_response(login_url, title=msg, msg=msg)
            return response
        return self.redirect_to_guard_view()
