from urllib.parse import urlencode

from django.conf import settings
from django.http.response import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.views import View
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request

from authentication.const import ConfirmType
from authentication.permissions import UserConfirmation
from common.sdk.im.slack import URL, SLACK_REDIRECT_URI_SESSION_KEY
from common.utils import get_logger
from common.utils.django import reverse
from common.utils.random import random_string
from common.views.mixins import PermissionsMixin, UserConfirmRequiredExceptionMixin
from users.views import UserVerifyPasswordView
from .base import BaseLoginCallbackView, BaseBindCallbackView
from .mixins import FlashMessageMixin

logger = get_logger(__file__)

SLACK_STATE_SESSION_KEY = '_slack_state'


class SlackMixin(UserConfirmRequiredExceptionMixin, PermissionsMixin, FlashMessageMixin, View):
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except APIException as e:
            msg = str(e.detail)
            return self.get_failed_response(
                '/',
                _('Slack Error'),
                msg
            )

    def verify_state(self):
        state = self.request.GET.get('state')
        session_state = self.request.session.get(SLACK_STATE_SESSION_KEY)
        if state != session_state:
            return False
        return True

    def get_verify_state_failed_response(self, redirect_uri):
        msg = _("The system configuration is incorrect. Please contact your administrator")
        return self.get_failed_response(redirect_uri, msg, msg)

    def get_qr_url(self, redirect_uri):
        state = random_string(16)
        self.request.session[SLACK_STATE_SESSION_KEY] = state

        params = {
            'client_id': settings.SLACK_CLIENT_ID,
            'state': state, 'scope': 'users:read,users:read.email',
            'redirect_uri': redirect_uri,
        }
        url = URL().AUTHORIZE + '?' + urlencode(params)
        return url

    def get_already_bound_response(self, redirect_url):
        msg = _('Slack is already bound')
        response = self.get_failed_response(redirect_url, msg, msg)
        return response


class SlackQRBindView(SlackMixin, View):
    permission_classes = (IsAuthenticated, UserConfirmation.require(ConfirmType.RELOGIN))

    def get(self, request: Request):
        redirect_url = request.GET.get('redirect_url')

        redirect_uri = reverse('authentication:slack-qr-bind-callback', external=True)
        redirect_uri += '?' + urlencode({'redirect_url': redirect_url})
        self.request.session[SLACK_REDIRECT_URI_SESSION_KEY] = redirect_uri
        url = self.get_qr_url(redirect_uri)
        return HttpResponseRedirect(url)


class SlackQRBindCallbackView(SlackMixin, BaseBindCallbackView):
    permission_classes = (IsAuthenticated,)

    client_type_path = 'common.sdk.im.slack.Slack'
    client_auth_params = {'client_id': 'SLACK_CLIENT_ID', 'client_secret': 'SLACK_CLIENT_SECRET'}
    auth_type = 'slack'
    auth_type_label = _('Slack')


class SlackEnableStartView(UserVerifyPasswordView):

    def get_success_url(self):
        referer = self.request.META.get('HTTP_REFERER')
        redirect_url = self.request.GET.get("redirect_url")

        success_url = reverse('authentication:slack-qr-bind')
        success_url += '?' + urlencode({
            'redirect_url': redirect_url or referer
        })

        return success_url


class SlackQRLoginView(SlackMixin, View):
    permission_classes = (AllowAny,)

    def get(self, request: Request):
        redirect_url = request.GET.get('redirect_url') or reverse('index')
        redirect_uri = reverse('authentication:slack-qr-login-callback', external=True)
        redirect_uri += '?' + urlencode({
            'redirect_url': redirect_url,
        })
        self.request.session[SLACK_REDIRECT_URI_SESSION_KEY] = redirect_uri
        url = self.get_qr_url(redirect_uri)
        return HttpResponseRedirect(url)


class SlackQRLoginCallbackView(SlackMixin, BaseLoginCallbackView):
    permission_classes = (AllowAny,)

    client_type_path = 'common.sdk.im.slack.Slack'
    client_auth_params = {'client_id': 'SLACK_CLIENT_ID', 'client_secret': 'SLACK_CLIENT_SECRET'}
    user_type = 'slack'
    auth_backend = 'AUTH_BACKEND_SLACK'

    msg_client_err = _('Slack Error')
    msg_user_not_bound_err = _('Slack is not bound')
    msg_not_found_user_from_client_err = _('Failed to get user from Slack')
