from django.http.response import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from urllib.parse import urlencode
from django.views import View
from django.conf import settings
from django.http.request import HttpRequest
from django.db.utils import IntegrityError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import APIException

from users.models import User
from users.views import UserVerifyPasswordView
from common.utils import get_logger, FlashMessageUtil
from common.utils.random import random_string
from common.utils.django import reverse, get_object_or_none
from common.mixins.views import UserConfirmRequiredExceptionMixin, PermissionsMixin
from common.permissions import UserConfirmation
from common.sdk.im.feishu import FeiShu, URL
from common.utils.common import get_request_ip_or_data
from authentication import errors
from authentication.const import ConfirmType
from authentication.mixins import AuthMixin
from authentication.notifications import OAuthBindMessage

logger = get_logger(__file__)

FEISHU_STATE_SESSION_KEY = '_feishu_state'


class FeiShuQRMixin(UserConfirmRequiredExceptionMixin, PermissionsMixin, View):
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except APIException as e:
            msg = str(e.detail)
            return self.get_failed_response(
                '/',
                _('FeiShu Error'),
                msg
            )

    def verify_state(self):
        state = self.request.GET.get('state')
        session_state = self.request.session.get(FEISHU_STATE_SESSION_KEY)
        if state != session_state:
            return False
        return True

    def get_verify_state_failed_response(self, redirect_uri):
        msg = _("The system configuration is incorrect. Please contact your administrator")
        return self.get_failed_response(redirect_uri, msg, msg)

    def get_qr_url(self, redirect_uri):
        state = random_string(16)
        self.request.session[FEISHU_STATE_SESSION_KEY] = state

        params = {
            'app_id': settings.FEISHU_APP_ID,
            'state': state,
            'redirect_uri': redirect_uri,
        }
        url = URL().authen + '?' + urlencode(params)
        return url

    @staticmethod
    def get_success_response(redirect_url, title, msg):
        message_data = {
            'title': title,
            'message': msg,
            'interval': 5,
            'redirect_url': redirect_url,
        }
        return FlashMessageUtil.gen_and_redirect_to(message_data)

    @staticmethod
    def get_failed_response(redirect_url, title, msg):
        message_data = {
            'title': title,
            'error': msg,
            'interval': 5,
            'redirect_url': redirect_url,
        }
        return FlashMessageUtil.gen_and_redirect_to(message_data)

    def get_already_bound_response(self, redirect_url):
        msg = _('FeiShu is already bound')
        response = self.get_failed_response(redirect_url, msg, msg)
        return response


class FeiShuQRBindView(FeiShuQRMixin, View):
    permission_classes = (IsAuthenticated, UserConfirmation.require(ConfirmType.ReLogin))

    def get(self, request: HttpRequest):
        user = request.user
        redirect_url = request.GET.get('redirect_url')

        redirect_uri = reverse('authentication:feishu-qr-bind-callback', external=True)
        redirect_uri += '?' + urlencode({'redirect_url': redirect_url})

        url = self.get_qr_url(redirect_uri)
        return HttpResponseRedirect(url)


class FeiShuQRBindCallbackView(FeiShuQRMixin, View):
    permission_classes = (IsAuthenticated,)

    def get(self, request: HttpRequest):
        code = request.GET.get('code')
        redirect_url = request.GET.get('redirect_url')

        if not self.verify_state():
            return self.get_verify_state_failed_response(redirect_url)

        user = request.user

        if user.feishu_id:
            response = self.get_already_bound_response(redirect_url)
            return response

        feishu = FeiShu(
            app_id=settings.FEISHU_APP_ID,
            app_secret=settings.FEISHU_APP_SECRET
        )
        user_id = feishu.get_user_id_by_code(code)

        if not user_id:
            msg = _('FeiShu query user failed')
            response = self.get_failed_response(redirect_url, msg, msg)
            return response

        try:
            user.feishu_id = user_id
            user.save()
        except IntegrityError as e:
            if e.args[0] == 1062:
                msg = _('The FeiShu is already bound to another user')
                response = self.get_failed_response(redirect_url, msg, msg)
                return response
            raise e

        ip = get_request_ip_or_data(request)
        OAuthBindMessage(user, ip, _('FeiShu'), user_id).publish_async()
        msg = _('Binding FeiShu successfully')
        response = self.get_success_response(redirect_url, msg, msg)
        return response


class FeiShuEnableStartView(UserVerifyPasswordView):

    def get_success_url(self):
        referer = self.request.META.get('HTTP_REFERER')
        redirect_url = self.request.GET.get("redirect_url")

        success_url = reverse('authentication:feishu-qr-bind')

        success_url += '?' + urlencode({
            'redirect_url': redirect_url or referer
        })

        return success_url


class FeiShuQRLoginView(FeiShuQRMixin, View):
    permission_classes = (AllowAny,)

    def get(self, request: HttpRequest):
        redirect_url = request.GET.get('redirect_url') or reverse('index')
        redirect_uri = reverse('authentication:feishu-qr-login-callback', external=True)
        redirect_uri += '?' + urlencode({
            'redirect_url': redirect_url,
        })

        url = self.get_qr_url(redirect_uri)
        return HttpResponseRedirect(url)


class FeiShuQRLoginCallbackView(AuthMixin, FeiShuQRMixin, View):
    permission_classes = (AllowAny,)

    def get(self, request: HttpRequest):
        code = request.GET.get('code')
        redirect_url = request.GET.get('redirect_url')
        login_url = reverse('authentication:login')

        if not self.verify_state():
            return self.get_verify_state_failed_response(redirect_url)

        feishu = FeiShu(
            app_id=settings.FEISHU_APP_ID,
            app_secret=settings.FEISHU_APP_SECRET
        )
        user_id = feishu.get_user_id_by_code(code)
        if not user_id:
            # 正常流程不会出这个错误，hack 行为
            msg = _('Failed to get user from FeiShu')
            response = self.get_failed_response(login_url, title=msg, msg=msg)
            return response

        user = get_object_or_none(User, feishu_id=user_id)
        if user is None:
            title = _('FeiShu is not bound')
            msg = _('Please login with a password and then bind the FeiShu')
            response = self.get_failed_response(login_url, title=title, msg=msg)
            return response

        try:
            self.check_oauth2_auth(user, settings.AUTH_BACKEND_FEISHU)
        except errors.AuthFailedError as e:
            self.set_login_failed_mark()
            msg = e.msg
            response = self.get_failed_response(login_url, title=msg, msg=msg)
            return response

        return self.redirect_to_guard_view()
