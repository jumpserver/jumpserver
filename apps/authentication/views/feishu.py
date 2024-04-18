from urllib.parse import urlencode

from django.conf import settings
from django.http.request import HttpRequest
from django.http.response import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.views import View
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny, IsAuthenticated

from authentication.const import ConfirmType
from authentication.permissions import UserConfirmation
from common.sdk.im.feishu import URL
from common.utils import get_logger
from common.utils.django import reverse
from common.utils.random import random_string
from common.views.mixins import PermissionsMixin, UserConfirmRequiredExceptionMixin
from users.views import UserVerifyPasswordView
from .base import BaseLoginCallbackView, BaseBindCallbackView
from .mixins import FlashMessageMixin

logger = get_logger(__file__)


class FeiShuEnableStartView(UserVerifyPasswordView):
    category = 'feishu'

    def get_success_url(self):
        referer = self.request.META.get('HTTP_REFERER')
        redirect_url = self.request.GET.get("redirect_url")

        success_url = reverse(f'authentication:{self.category}-qr-bind')

        success_url += '?' + urlencode({
            'redirect_url': redirect_url or referer
        })

        return success_url


class FeiShuQRMixin(UserConfirmRequiredExceptionMixin, PermissionsMixin, FlashMessageMixin, View):
    category = 'feishu'
    error = _('FeiShu Error')
    error_msg = _('FeiShu is already bound')
    state_session_key = f'_{category}_state'

    @property
    def url_object(self):
        return URL()

    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except APIException as e:
            msg = str(e.detail)
            return self.get_failed_response(
                '/', self.error, msg
            )

    def verify_state(self):
        state = self.request.GET.get('state')
        session_state = self.request.session.get(self.state_session_key)
        if state != session_state:
            return False
        return True

    def get_verify_state_failed_response(self, redirect_uri):
        msg = _("The system configuration is incorrect. Please contact your administrator")
        return self.get_failed_response(redirect_uri, msg, msg)

    def get_qr_url(self, redirect_uri):
        state = random_string(16)
        self.request.session[self.state_session_key] = state

        params = {
            'app_id': getattr(settings, f'{self.category}_APP_ID'.upper()),
            'state': state,
            'redirect_uri': redirect_uri,
        }
        url = self.url_object.authen + '?' + urlencode(params)
        return url

    def get_already_bound_response(self, redirect_url):
        response = self.get_failed_response(redirect_url, self.error_msg, self.error_msg)
        return response


class FeiShuQRBindView(FeiShuQRMixin, View):
    permission_classes = (IsAuthenticated, UserConfirmation.require(ConfirmType.RELOGIN))

    def get(self, request: HttpRequest):
        redirect_url = request.GET.get('redirect_url')

        redirect_uri = reverse(f'authentication:{self.category}-qr-bind-callback', external=True)
        redirect_uri += '?' + urlencode({'redirect_url': redirect_url})

        url = self.get_qr_url(redirect_uri)
        return HttpResponseRedirect(url)


class FeiShuQRBindCallbackView(FeiShuQRMixin, BaseBindCallbackView):
    permission_classes = (IsAuthenticated,)

    auth_type = 'feishu'
    auth_type_label = _('FeiShu')
    client_type_path = f'common.sdk.im.{auth_type}.FeiShu'

    @property
    def client_auth_params(self):
        return {
            'app_id': f'{self.auth_type}_APP_ID'.upper(),
            'app_secret': f'{self.auth_type}_APP_SECRET'.upper()
        }


class FeiShuQRLoginView(FeiShuQRMixin, View):
    permission_classes = (AllowAny,)

    def get(self, request: HttpRequest):
        redirect_url = request.GET.get('redirect_url') or reverse('index')
        redirect_uri = reverse(f'authentication:{self.category}-qr-login-callback', external=True)
        redirect_uri += '?' + urlencode({
            'redirect_url': redirect_url,
        })

        url = self.get_qr_url(redirect_uri)
        return HttpResponseRedirect(url)


class FeiShuQRLoginCallbackView(FeiShuQRMixin, BaseLoginCallbackView):
    permission_classes = (AllowAny,)

    user_type = 'feishu'
    auth_type = user_type
    client_type_path = f'common.sdk.im.{auth_type}.FeiShu'

    msg_client_err = _('FeiShu Error')
    msg_user_not_bound_err = _('FeiShu is not bound')
    msg_not_found_user_from_client_err = _('Failed to get user from FeiShu')

    auth_backend = f'AUTH_BACKEND_{auth_type}'.upper()

    @property
    def client_auth_params(self):
        return {
            'app_id': f'{self.auth_type}_APP_ID'.upper(),
            'app_secret': f'{self.auth_type}_APP_SECRET'.upper()
        }
