# ~*~ coding: utf-8 ~*~
#

from __future__ import unicode_literals
import os
import datetime
from django.core.cache import cache
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.http import HttpResponse
from django.shortcuts import reverse, redirect
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.base import TemplateView, RedirectView
from django.views.generic.edit import FormView
from django.conf import settings
from django.urls import reverse_lazy

from common.utils import get_request_ip, get_object_or_none
from users.models import User
from users.utils import (
    get_user_or_tmp_user, increase_login_failed_count,
    redirect_user_first_login_or_index
)
from ..signals import post_auth_success, post_auth_failed
from .. import forms, mixins, errors


__all__ = [
    'UserLoginView', 'UserLogoutView',
    'UserLoginGuardView', 'UserLoginWaitConfirmView',
]


@method_decorator(sensitive_post_parameters(), name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UserLoginView(mixins.AuthMixin, FormView):
    form_class = forms.UserLoginForm
    form_class_captcha = forms.UserLoginCaptchaForm
    key_prefix_captcha = "_LOGIN_INVALID_{}"
    redirect_field_name = 'next'

    def get_template_names(self):
        template_name = 'authentication/login.html'
        if not settings.XPACK_ENABLED:
            return template_name

        from xpack.plugins.license.models import License
        if not License.has_valid_license():
            return template_name

        template_name = 'authentication/xpack_login.html'
        return template_name

    def get(self, request, *args, **kwargs):
        if request.user.is_staff:
            return redirect(redirect_user_first_login_or_index(
                request, self.redirect_field_name)
            )
        # show jumpserver login page if request http://{JUMP-SERVER}/?admin=1
        if settings.AUTH_OPENID and not self.request.GET.get('admin', 0):
            query_string = request.GET.urlencode()
            login_url = "{}?{}".format(settings.LOGIN_URL, query_string)
            return redirect(login_url)
        request.session.set_test_cookie()
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        if not self.request.session.test_cookie_worked():
            return HttpResponse(_("Please enable cookies and try again."))
        try:
            self.check_user_auth()
        except errors.AuthFailedError as e:
            form.add_error(None, e.msg)
            ip = self.get_request_ip()
            cache.set(self.key_prefix_captcha.format(ip), 1, 3600)
            context = self.get_context_data(form=form)
            return self.render_to_response(context)
        return self.redirect_to_guard_view()

    def redirect_to_guard_view(self):
        guard_url = reverse('authentication:login-guard')
        args = self.request.META.get('QUERY_STRING', '')
        if args and self.query_string:
            guard_url = "%s?%s" % (guard_url, args)
        return redirect(guard_url)

    def get_form_class(self):
        ip = get_request_ip(self.request)
        if cache.get(self.key_prefix_captcha.format(ip)):
            return self.form_class_captcha
        else:
            return self.form_class

    def get_context_data(self, **kwargs):
        context = {
            'demo_mode': os.environ.get("DEMO_MODE"),
            'AUTH_OPENID': settings.AUTH_OPENID,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserLoginGuardView(mixins.AuthMixin, RedirectView):
    redirect_field_name = 'next'
    login_url = reverse_lazy('authentication:login')
    login_otp_url = reverse_lazy('authentication:login-otp')
    login_confirm_url = reverse_lazy('authentication:login-wait-confirm')

    def format_redirect_url(self, url):
        args = self.request.META.get('QUERY_STRING', '')
        if args and self.query_string:
            url = "%s?%s" % (url, args)
        return url

    def get_redirect_url(self, *args, **kwargs):
        if not self.request.session.get('auth_password'):
            return self.format_redirect_url(self.login_url)
        user = self.get_user_from_session()
        # 启用并设置了otp
        if user.otp_enabled and user.otp_secret_key and \
                not self.request.session.get('auth_mfa'):
            return self.format_redirect_url(self.login_otp_url)
        confirm_setting = user.get_login_confirm_setting()
        if confirm_setting and not self.request.session.get('auth_confirm'):
            order = confirm_setting.create_confirm_order(self.request)
            self.request.session['auth_order_id'] = str(order.id)
            url = self.format_redirect_url(self.login_confirm_url)
            return url
        self.login_success(user)
        self.clear_auth_mark()
        # 启用但是没有设置otp
        if user.otp_enabled and not user.otp_secret_key:
            # 1,2,mfa_setting & F
            return reverse('users:user-otp-enable-authentication')
        url = redirect_user_first_login_or_index(
            self.request, self.redirect_field_name
        )
        return url

    def login_success(self, user):
        auth_login(self.request, user)
        self.send_auth_signal(success=True, user=user)

    def send_auth_signal(self, success=True, user=None, username='', reason=''):
        if success:
            post_auth_success.send(sender=self.__class__, user=user, request=self.request)
        else:
            post_auth_failed.send(
                sender=self.__class__, username=username,
                request=self.request, reason=reason
            )


class UserLoginWaitConfirmView(TemplateView):
    template_name = 'authentication/login_wait_confirm.html'

    def get_context_data(self, **kwargs):
        from orders.models import LoginConfirmOrder
        order_id = self.request.session.get("auth_order_id")
        if not order_id:
            order = None
        else:
            order = get_object_or_none(LoginConfirmOrder, pk=order_id)
        context = super().get_context_data(**kwargs)
        if order:
            order_detail_url = reverse('orders:login-confirm-order-detail', kwargs={'pk': order_id})
            timestamp_created = datetime.datetime.timestamp(order.date_created)
            msg = _("""Wait for <b>{}</b> confirm, You also can copy link to her/him <br/>
                  Don't close this page""").format(order.assignees_display)
        else:
            timestamp_created = 0
            order_detail_url = ''
            msg = _("No order found")
        context.update({
            "msg": msg,
            "timestamp": timestamp_created,
            "order_detail_url": order_detail_url
        })
        return context


@method_decorator(never_cache, name='dispatch')
class UserLogoutView(TemplateView):
    template_name = 'flash_message_standalone.html'

    def get(self, request, *args, **kwargs):
        auth_logout(request)
        next_uri = request.COOKIES.get("next")
        if next_uri:
            return redirect(next_uri)
        response = super().get(request, *args, **kwargs)
        return response

    def get_context_data(self, **kwargs):
        context = {
            'title': _('Logout success'),
            'messages': _('Logout success, return login page'),
            'interval': 1,
            'redirect_url': reverse('authentication:login'),
            'auto_redirect': True,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)



