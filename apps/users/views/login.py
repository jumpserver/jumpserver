# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals
import os
from django import forms
from django.shortcuts import render
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView
from django.core.files.storage import default_storage
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import reverse, redirect
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from formtools.wizard.views import SessionWizardView
from django.conf import settings
from django.utils import timezone

from common.utils import get_object_or_none
from common.mixins import DatetimeSearchMixin
from ..models import User, LoginLog
from ..utils import send_reset_password_mail
from ..tasks import write_login_log_async
from .. import forms


__all__ = [
    'UserLoginView', 'UserLogoutView',
    'UserForgotPasswordView', 'UserForgotPasswordSendmailSuccessView',
    'UserResetPasswordView', 'UserResetPasswordSuccessView',
    'UserFirstLoginView', 'LoginLogListView'
]


@method_decorator(sensitive_post_parameters(), name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UserLoginView(FormView):
    template_name = 'users/login.html'
    form_class = forms.UserLoginForm
    redirect_field_name = 'next'

    def get(self, request, *args, **kwargs):
        if request.user.is_staff:
            return redirect(self.get_success_url())
        request.session.set_test_cookie()
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        if not self.request.session.test_cookie_worked():
            return HttpResponse(_("Please enable cookies and try again."))
        auth_login(self.request, form.get_user())
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')

        if x_forwarded_for and x_forwarded_for[0]:
            login_ip = x_forwarded_for[0]
        else:
            login_ip = self.request.META.get('REMOTE_ADDR', '')
        user_agent = self.request.META.get('HTTP_USER_AGENT', '')
        write_login_log_async.delay(
            self.request.user.username, type='W',
            ip=login_ip, user_agent=user_agent
        )
        return redirect(self.get_success_url())

    def get_success_url(self):
        if self.request.user.is_first_login:
            return reverse('users:user-first-login')

        return self.request.POST.get(
            self.redirect_field_name,
            self.request.GET.get(self.redirect_field_name, reverse('index')))

    def get_context_data(self, **kwargs):
        context = {
            'demo_mode': os.environ.get("DEMO_MODE"),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


@method_decorator(never_cache, name='dispatch')
class UserLogoutView(TemplateView):
    template_name = 'flash_message_standalone.html'

    def get(self, request, *args, **kwargs):
        auth_logout(request)
        response = super().get(request, *args, **kwargs)
        return response

    def get_context_data(self, **kwargs):
        context = {
            'title': _('Logout success'),
            'messages': _('Logout success, return login page'),
            'interval': 1,
            'redirect_url': reverse('users:login'),
            'auto_redirect': True,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserForgotPasswordView(TemplateView):
    template_name = 'users/forgot_password.html'

    def post(self, request):
        email = request.POST.get('email')
        user = get_object_or_none(User, email=email)
        if not user:
            return self.get(request, errors=_('Email address invalid, '
                                              'please input again'))
        else:
            send_reset_password_mail(user)
            return HttpResponseRedirect(
                reverse('users:forgot-password-sendmail-success'))


class UserForgotPasswordSendmailSuccessView(TemplateView):
    template_name = 'flash_message_standalone.html'

    def get_context_data(self, **kwargs):
        context = {
            'title': _('Send reset password message'),
            'messages': _('Send reset password mail success, '
                          'login your mail box and follow it '),
            'redirect_url': reverse('users:login'),
        }
        kwargs.update(context)
        return super()\
            .get_context_data(**kwargs)


class UserResetPasswordSuccessView(TemplateView):
    template_name = 'flash_message_standalone.html'

    def get_context_data(self, **kwargs):
        context = {
            'title': _('Reset password success'),
            'messages': _('Reset password success, return to login page'),
            'redirect_url': reverse('users:login'),
            'auto_redirect': True,
        }
        kwargs.update(context)
        return super()\
            .get_context_data(**kwargs)


class UserResetPasswordView(TemplateView):
    template_name = 'users/reset_password.html'

    def get(self, request, *args, **kwargs):
        token = request.GET.get('token')
        user = User.validate_reset_token(token)

        if not user:
            kwargs.update({'errors': _('Token invalid or expired')})
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        password = request.POST.get('password')
        password_confirm = request.POST.get('password-confirm')
        token = request.GET.get('token')

        if password != password_confirm:
            return self.get(request, errors=_('Password not same'))

        user = User.validate_reset_token(token)
        if not user:
            return self.get(request, errors=_('Token invalid or expired'))

        user.reset_password(password)
        return HttpResponseRedirect(reverse('users:reset-password-success'))


class UserFirstLoginView(LoginRequiredMixin, SessionWizardView):
    template_name = 'users/first_login.html'
    form_list = [forms.UserProfileForm, forms.UserPublicKeyForm]
    file_storage = default_storage

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated() and not request.user.is_first_login:
            return redirect(reverse('index'))
        return super().dispatch(request, *args, **kwargs)

    def done(self, form_list, **kwargs):
        user = self.request.user
        for form in form_list:
            for field in form:
                if field.value():
                    setattr(user, field.name, field.value())
                if field.name == 'enable_otp':
                    user.enable_otp = field.value()
        user.is_first_login = False
        user.is_public_key_valid = True
        user.save()
        context = {
            'user_guide_url': settings.USER_GUIDE_URL
        }
        return render(self.request, 'users/first_login_done.html', context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'app': _('Users'), 'action': _('First login')})
        return context

    def get_form_initial(self, step):
        user = self.request.user
        if step == '0':
            return {
                'username': user.username or '',
                'name': user.name or user.username,
                'email': user.email or '',
                'wechat': user.wechat or '',
                'phone': user.phone or ''
            }
        return super().get_form_initial(step)

    def get_form(self, step=None, data=None, files=None):
        form = super().get_form(step, data, files)

        form.instance = self.request.user
        return form


class LoginLogListView(DatetimeSearchMixin, ListView):
    template_name = 'users/login_log_list.html'
    model = LoginLog
    paginate_by = settings.DISPLAY_PER_PAGE
    user = keyword = ""
    date_to = date_from = None

    def get_queryset(self):
        self.user = self.request.GET.get('user', '')
        self.keyword = self.request.GET.get("keyword", '')

        queryset = super().get_queryset()
        queryset = queryset.filter(
            datetime__gt=self.date_from, datetime__lt=self.date_to
        )
        if self.user:
            queryset = queryset.filter(username=self.user)
        if self.keyword:
            queryset = queryset.filter(
                Q(ip__contains=self.keyword) |
                Q(city__contains=self.keyword) |
                Q(username__contains=self.keyword)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Users'),
            'action': _('Login log list'),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'user': self.user,
            'keyword': self.keyword,
            'user_list': set(LoginLog.objects.all().values_list('username', flat=True))
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)