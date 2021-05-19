import urllib

from django.http.response import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.cache import never_cache
from django.views.generic import TemplateView
from django.views import View
from django.conf import settings
from django.http.request import HttpRequest
from django.db.utils import IntegrityError
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import APIException

from users.views import UserVerifyPasswordView
from users.utils import is_auth_password_time_valid
from users.models import User
from common.utils import get_logger
from common.utils.random import random_string
from common.utils.django import reverse, get_object_or_none
from common.message.backends.wecom import URL
from common.message.backends.wecom import WeCom
from common.mixins.views import PermissionsMixin
from authentication import errors
from authentication.mixins import AuthMixin

logger = get_logger(__file__)


WECOM_STATE_SESSION_KEY = '_wecom_state'


class WeComQRMixin(PermissionsMixin, View):
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except APIException as e:
            try:
                msg = e.detail['errmsg']
            except Exception:
                msg = _('WeCom Error, Please contact your system administrator')
            return self.get_failed_reponse(
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
        msg = _("You've been hacked")
        return self.get_failed_reponse(redirect_uri, msg, msg)

    def get_qr_url(self, redirect_uri):
        state = random_string(16)
        self.request.session[WECOM_STATE_SESSION_KEY] = state

        params = {
            'appid': settings.WECOM_CORPID,
            'agentid': settings.WECOM_AGENTID,
            'state': state,
            'redirect_uri': redirect_uri,
        }
        url = URL.QR_CONNECT + '?' + urllib.parse.urlencode(params)
        return url

    def get_success_reponse(self, redirect_url, title, msg):
        ok_flash_msg_url = reverse('authentication:wecom-bind-success-flash-msg')
        ok_flash_msg_url += '?' + urllib.parse.urlencode({
            'redirect_url': redirect_url,
            'title': title,
            'msg': msg
        })
        return HttpResponseRedirect(ok_flash_msg_url)

    def get_failed_reponse(self, redirect_url, title, msg):
        failed_flash_msg_url = reverse('authentication:wecom-bind-failed-flash-msg')
        failed_flash_msg_url += '?' + urllib.parse.urlencode({
            'redirect_url': redirect_url,
            'title': title,
            'msg': msg
        })
        return HttpResponseRedirect(failed_flash_msg_url)

    def get_already_bound_response(self, redirect_url):
        msg = _('WeCom is already bound')
        response = self.get_failed_reponse(redirect_url, msg, msg)
        return response


class WeComQRBindView(WeComQRMixin, View):
    permission_classes = (IsAuthenticated,)

    def get(self, request: HttpRequest):
        user = request.user
        redirect_url = request.GET.get('redirect_url')

        if not is_auth_password_time_valid(request.session):
            msg = _('Please verify your password first')
            response = self.get_failed_reponse(redirect_url, msg, msg)
            return response

        redirect_uri = reverse('authentication:wecom-qr-bind-callback', kwargs={'user_id': user.id}, external=True)
        redirect_uri += '?' + urllib.parse.urlencode({'redirect_url': redirect_url})

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
            response = self.get_failed_reponse(redirect_url, msg, msg)
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
            response = self.get_failed_reponse(redirect_url, msg, msg)
            return response

        try:
            user.wecom_id = wecom_userid
            user.save()
        except IntegrityError as e:
            if e.args[0] == 1062:
                msg = _('The WeCom is already bound to another user')
                response = self.get_failed_reponse(redirect_url, msg, msg)
                return response
            raise e

        msg = _('Binding WeCom successfully')
        response = self.get_success_reponse(redirect_url, msg, msg)
        return response


class WeComEnableStartView(UserVerifyPasswordView):

    def get_success_url(self):
        referer = self.request.META.get('HTTP_REFERER')
        redirect_url = self.request.GET.get("redirect_url")

        success_url = reverse('authentication:wecom-qr-bind')

        success_url += '?' + urllib.parse.urlencode({
            'redirect_url': redirect_url or referer
        })

        return success_url


class WeComQRLoginView(WeComQRMixin, View):
    permission_classes = (AllowAny,)

    def get(self,  request: HttpRequest):
        redirect_url = request.GET.get('redirect_url')

        redirect_uri = reverse('authentication:wecom-qr-login-callback', external=True)
        redirect_uri += '?' + urllib.parse.urlencode({'redirect_url': redirect_url})

        url = self.get_qr_url(redirect_uri)
        return HttpResponseRedirect(url)


class WeComQRLoginCallbackView(AuthMixin, WeComQRMixin, View):
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
            response = self.get_failed_reponse(login_url, title=msg, msg=msg)
            return response

        user = get_object_or_none(User, wecom_id=wecom_userid)
        if user is None:
            title = _('WeCom is not bound')
            msg = _('Please login with a password and then bind the WeCom')
            response = self.get_failed_reponse(login_url, title=title, msg=msg)
            return response

        try:
            self.check_oauth2_auth(user, settings.AUTH_BACKEND_WECOM)
        except errors.AuthFailedError as e:
            self.set_login_failed_mark()
            msg = e.msg
            response = self.get_failed_reponse(login_url, title=msg, msg=msg)
            return response

        return self.redirect_to_guard_view()


@method_decorator(never_cache, name='dispatch')
class FlashWeComBindSucceedMsgView(TemplateView):
    template_name = 'flash_message_standalone.html'

    def get(self, request, *args, **kwargs):
        title = request.GET.get('title')
        msg = request.GET.get('msg')

        context = {
            'title': title or _('Binding WeCom successfully'),
            'messages': msg or _('Binding WeCom successfully'),
            'interval': 5,
            'redirect_url': request.GET.get('redirect_url'),
            'auto_redirect': True,
        }
        return self.render_to_response(context)


@method_decorator(never_cache, name='dispatch')
class FlashWeComBindFailedMsgView(TemplateView):
    template_name = 'flash_message_standalone.html'

    def get(self, request, *args, **kwargs):
        title = request.GET.get('title')
        msg = request.GET.get('msg')

        context = {
            'title': title or _('Binding WeCom failed'),
            'messages': msg or _('Binding WeCom failed'),
            'interval': 5,
            'redirect_url': request.GET.get('redirect_url'),
            'auto_redirect': True,
        }
        return self.render_to_response(context)
