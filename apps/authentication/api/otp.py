# -*- coding: utf-8 -*-
#
from django.urls import reverse
from django.utils.translation import ugettext as _
from django.contrib.auth import logout as auth_logout
from rest_framework.generics import CreateAPIView
from rest_framework.views import Response

from authentication.mfa import MFAOtp
from authentication.const import OTP_FAILED_MSG, PROFILE_USER_MFA_URL
from common.utils import get_logger, FlashMessageUtil, reverse
from common.permissions import IsValidUserOrSessionUser
from users.utils import get_user_or_pre_auth_user, check_otp_code
from ..mixins import AuthMixin


logger = get_logger(__name__)


class UserOtpEnableBindApi(AuthMixin, CreateAPIView):
    permission_classes = [IsValidUserOrSessionUser]

    def bind(self, request, *args, **kwargs):
        pre_response = self._pre_check_can_bind()
        if pre_response:
            return pre_response

        otp_code = request.data.get('otp_code')
        otp_secret_key = request.data.get('otp_secret_key', '')

        valid = check_otp_code(otp_secret_key, otp_code)
        if not valid:
            return Response(data={'error': OTP_FAILED_MSG}, status=400)
        self.save_otp(otp_secret_key)
        auth_logout(self.request)

        redirect_url = self.get_success_bound_redirect_url()
        return Response(data={'redirect': redirect_url}, status=200)

    def disabled(self, request, *args, **kwargs):
        user = self.request.user
        otp_code = request.data.get('otp_code')

        otp = MFAOtp(user)
        ok, error = otp.check_code(otp_code)
        if not ok:
            return Response(data={'error': error}, status=400)

        otp.disable()
        auth_logout(self.request)

        redirect_url = self.get_disabled_success_url()
        return Response(data={'redirect': redirect_url}, status=200)

    def post(self, request, *args, **kwargs):
        action_mapping = {
            'bind': self.bind,
            'disabled': self.disabled
        }

        action = request.data.get('action')
        handler = action_mapping.get(action)
        if not handler:
            err = _("The parameter 'action' must be [{}]".format(','.join(action_mapping.keys())))
            return Response(data={'error': err}, status=400)

        return handler(request, *args, **kwargs)

    def _pre_check_can_bind(self):
        try:
            user = self.get_user_from_session()
        except Exception as e:
            return Response(data={'error': e}, status=400)

        if user.otp_secret_key:
            redirect_url = self.get_already_bound_redirect_url()
            return Response(data={'redirect': redirect_url}, status=200)
        return None

    @staticmethod
    def get_already_bound_redirect_url():
        message_data = {
            'title': _('Already bound'),
            'error': _('MFA already bound, disable first, then bound'),
            'interval': 10,
            'redirect_url': PROFILE_USER_MFA_URL,
        }
        redirect_url = FlashMessageUtil.gen_message_url(message_data)
        return redirect_url

    @staticmethod
    def get_disabled_success_url():
        message_data = {
            'title': _('OTP disable success'),
            'message': _('OTP disable success, return login page'),
            'interval': 5,
            'redirect_url': reverse('api-auth:login'),
        }
        redirect_url = FlashMessageUtil.gen_message_url(message_data)
        return redirect_url

    def save_otp(self, otp_secret_key):
        user = get_user_or_pre_auth_user(self.request)
        user.otp_secret_key = otp_secret_key
        user.save(update_fields=['otp_secret_key'])

    @staticmethod
    def get_success_bound_redirect_url():
        message_data = {
            'title': _('OTP enable success'),
            'message': _('OTP enable success, return login page'),
            'interval': 5,
            'redirect_url': reverse('api-auth:login'),
        }
        redirect_url = FlashMessageUtil.gen_message_url(message_data)
        return redirect_url
