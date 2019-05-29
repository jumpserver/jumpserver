# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals

import json
import uuid
import csv
import codecs
import chardet
from io import StringIO

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.messages.views import SuccessMessageMixin
from django.core.cache import cache
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic.base import TemplateView
from django.db import transaction
from django.views.generic.edit import (
    CreateView, UpdateView, FormView
)
from django.views.generic.detail import DetailView
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import logout as auth_logout

from common.const import (
    create_success_msg, update_success_msg, KEY_CACHE_RESOURCES_ID
)
from common.mixins import JSONResponseMixin
from common.utils import get_logger, get_object_or_none, is_uuid, ssh_key_gen
from common.permissions import AdminUserRequiredMixin
from orgs.utils import current_org
from .. import forms
from ..models import User, UserGroup
from ..utils import generate_otp_uri, check_otp_code, \
    get_user_or_tmp_user, get_password_check_rules, check_password_rules, \
    is_need_unblock
from ..signals import post_user_create

__all__ = [
    'UserListView', 'UserCreateView', 'UserDetailView',
    'UserUpdateView',
    'UserGrantedAssetView',
    'UserExportView',  'UserBulkImportView', 'UserProfileView',
    'UserProfileUpdateView', 'UserPasswordUpdateView',
    'UserPublicKeyUpdateView', 'UserBulkUpdateView',
    'UserPublicKeyGenerateView',
    'UserOtpEnableAuthenticationView', 'UserOtpEnableInstallAppView',
    'UserOtpEnableBindView', 'UserOtpSettingsSuccessView',
    'UserOtpDisableAuthenticationView', 'UserOtpUpdateView'
]

logger = get_logger(__name__)


class UserListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'users/user_list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'app': _('Users'),
            'action': _('User list'),
        })
        return context


class UserCreateView(AdminUserRequiredMixin, SuccessMessageMixin, CreateView):
    model = User
    form_class = forms.UserCreateForm
    template_name = 'users/user_create.html'
    success_url = reverse_lazy('users:user-list')
    success_message = create_success_msg

    def get_context_data(self, **kwargs):
        check_rules = get_password_check_rules()
        context = {
            'app': _('Users'),
            'action': _('Create user'),
            'password_check_rules': check_rules,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        user = form.save(commit=False)
        user.created_by = self.request.user.username or 'System'
        user.save()
        if current_org and current_org.is_real():
            user.orgs.add(current_org.id)
        post_user_create.send(self.__class__, user=user)
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super(UserCreateView, self).get_form_kwargs()
        data = {'request': self.request}
        kwargs.update(data)
        return kwargs


class UserUpdateView(AdminUserRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    form_class = forms.UserUpdateForm
    template_name = 'users/user_update.html'
    context_object_name = 'user_object'
    success_url = reverse_lazy('users:user-list')
    success_message = update_success_msg

    def _deny_permission(self):
        obj = self.get_object()
        return not self.request.user.is_superuser and obj.is_superuser

    def get(self, request, *args, **kwargs):
        if self._deny_permission():
            return redirect(self.success_url)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        check_rules = get_password_check_rules()
        context = {
            'app': _('Users'),
            'action': _('Update user'),
            'password_check_rules': check_rules,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        password = form.cleaned_data.get('password')
        if not password:
            return super().form_valid(form)

        is_ok = check_password_rules(password)
        if not is_ok:
            form.add_error(
                "password", _("* Your password does not meet the requirements")
            )
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_form_kwargs(self):
        kwargs = super(UserUpdateView, self).get_form_kwargs()
        data = {'request': self.request}
        kwargs.update(data)
        return kwargs


class UserBulkUpdateView(AdminUserRequiredMixin, TemplateView):
    model = User
    form_class = forms.UserBulkUpdateForm
    template_name = 'users/user_bulk_update.html'
    success_url = reverse_lazy('users:user-list')
    success_message = _("Bulk update user success")
    form = None
    id_list = None

    def get(self, request, *args, **kwargs):
        spm = request.GET.get('spm', '')
        users_id = cache.get(KEY_CACHE_RESOURCES_ID.format(spm))
        if kwargs.get('form'):
            self.form = kwargs['form']
        elif users_id:
            self.form = self.form_class(initial={'users': users_id})
        else:
            self.form = self.form_class()
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, self.success_message)
            return redirect(self.success_url)
        else:
            return self.get(request, form=form, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Assets',
            'action': _('Bulk update user'),
            'form': self.form,
            'users_selected': self.id_list,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserDetailView(AdminUserRequiredMixin, DetailView):
    model = User
    template_name = 'users/user_detail.html'
    context_object_name = "user_object"
    key_prefix_block = "_LOGIN_BLOCK_{}"

    def get_context_data(self, **kwargs):
        user = self.get_object()
        key_block = self.key_prefix_block.format(user.username)
        groups = UserGroup.objects.exclude(id__in=self.object.groups.all())
        context = {
            'app': _('Users'),
            'action': _('User detail'),
            'groups': groups,
            'unblock': is_need_unblock(key_block),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        org_users = current_org.get_org_users().values_list('id', flat=True)
        queryset = queryset.filter(id__in=org_users)
        return queryset


@method_decorator(csrf_exempt, name='dispatch')
class UserExportView(View):
    def get(self, request):
        fields = [
            User._meta.get_field(name)
            for name in [
                'id', 'name', 'username', 'email', 'role',
                'wechat', 'phone', 'is_active', 'comment',
            ]
        ]
        spm = request.GET.get('spm', '')
        users_id = cache.get(spm, [])
        filename = 'users-{}.csv'.format(
            timezone.localtime(timezone.now()).strftime('%Y-%m-%d_%H-%M-%S')
        )
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        response.write(codecs.BOM_UTF8)
        users = User.objects.filter(id__in=users_id)
        writer = csv.writer(response, dialect='excel', quoting=csv.QUOTE_MINIMAL)

        header = [field.verbose_name for field in fields]
        header.append(_('User groups'))
        writer.writerow(header)

        for user in users:
            groups = ','.join([group.name for group in user.groups.all()])
            data = [getattr(user, field.name) for field in fields]
            data.append(groups)
            writer.writerow(data)

        return response

    def post(self, request):
        try:
            users_id = json.loads(request.body).get('users_id', [])
        except ValueError:
            return HttpResponse('Json object not valid', status=400)
        spm = uuid.uuid4().hex
        cache.set(spm, users_id, 300)
        url = reverse('users:user-export') + '?spm=%s' % spm
        return JsonResponse({'redirect': url})


class UserBulkImportView(AdminUserRequiredMixin, JSONResponseMixin, FormView):
    form_class = forms.FileForm

    def form_invalid(self, form):
        try:
            error = form.errors.values()[-1][-1]
        except Exception as e:
            error = _('Invalid file.')
        data = {
            'success': False,
            'msg': error
        }
        return self.render_json_response(data)

    # todo: need be patch, method to long
    def form_valid(self, form):
        f = form.cleaned_data['file']
        det_result = chardet.detect(f.read())
        f.seek(0)  # reset file seek index
        data = f.read().decode(det_result['encoding']).strip(codecs.BOM_UTF8.decode())
        csv_file = StringIO(data)
        reader = csv.reader(csv_file)
        csv_data = [row for row in reader]
        header_ = csv_data[0]
        fields = [
            User._meta.get_field(name)
            for name in [
                'id', 'name', 'username', 'email', 'role',
                'wechat', 'phone', 'is_active', 'comment',
            ]
        ]
        mapping_reverse = {field.verbose_name: field.name for field in fields}
        mapping_reverse[_('User groups')] = 'groups'
        attr = [mapping_reverse.get(n, None) for n in header_]
        if None in attr:
            data = {'valid': False,
                    'msg': 'Must be same format as '
                           'template or export file'}
            return self.render_json_response(data)

        created, updated, failed = [], [], []
        for row in csv_data[1:]:
            if set(row) == {''}:
                continue
            user_dict = dict(zip(attr, row))
            id_ = user_dict.pop('id')
            for k, v in user_dict.items():
                if k in ['is_active']:
                    if v.lower() == 'false':
                        v = False
                    else:
                        v = bool(v)
                elif k == 'groups':
                    groups_name = v.split(',')
                    v = UserGroup.objects.filter(name__in=groups_name)
                else:
                    continue
                user_dict[k] = v
            user = get_object_or_none(User, id=id_) if id_ and is_uuid(id_) else None
            if not user:
                try:
                    with transaction.atomic():
                        groups = user_dict.pop('groups')
                        user = User.objects.create(**user_dict)
                        user.groups.set(groups)
                        created.append(user_dict['username'])
                        post_user_create.send(self.__class__, user=user)
                except Exception as e:
                    failed.append('%s: %s' % (user_dict['username'], str(e)))
            else:
                for k, v in user_dict.items():
                    if k == 'groups':
                        user.groups.set(v)
                        continue
                    if v:
                        setattr(user, k, v)
                try:
                    user.save()
                    updated.append(user_dict['username'])
                except Exception as e:
                    failed.append('%s: %s' % (user_dict['username'], str(e)))

        data = {
            'created': created,
            'created_info': 'Created {}'.format(len(created)),
            'updated': updated,
            'updated_info': 'Updated {}'.format(len(updated)),
            'failed': failed,
            'failed_info': 'Failed {}'.format(len(failed)),
            'valid': True,
            'msg': 'Created: {}. Updated: {}, Error: {}'.format(
                len(created), len(updated), len(failed))
        }
        return self.render_json_response(data)


class UserGrantedAssetView(AdminUserRequiredMixin, DetailView):
    model = User
    template_name = 'users/user_granted_asset.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Users'),
            'action': _('User granted assets'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'users/user_profile.html'

    def get_context_data(self, **kwargs):
        mfa_setting = settings.SECURITY_MFA_AUTH
        context = {
            'action': _('Profile'),
            'mfa_setting': mfa_setting if mfa_setting is not None else False,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserProfileUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'users/user_profile_update.html'
    model = User
    form_class = forms.UserProfileForm
    success_url = reverse_lazy('users:user-profile')

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = {
            'app': _('User'),
            'action': _('Profile setting'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserPasswordUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'users/user_password_update.html'
    model = User
    form_class = forms.UserPasswordForm
    success_url = reverse_lazy('users:user-profile')

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        check_rules = get_password_check_rules()
        context = {
            'app': _('Users'),
            'action': _('Password update'),
            'password_check_rules': check_rules,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_success_url(self):
        auth_logout(self.request)
        return super().get_success_url()

    def form_valid(self, form):
        if not self.request.user.can_update_password():
            error = _("User auth from {}, go there change password").format(
                self.request.source_display
            )
            form.add_error("password", error)
            return self.form_invalid(form)
        password = form.cleaned_data.get('new_password')
        is_ok = check_password_rules(password)
        if not is_ok:
            form.add_error(
                "new_password",
                _("* Your password does not meet the requirements")
            )
            return self.form_invalid(form)
        return super().form_valid(form)


class UserPublicKeyUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'users/user_pubkey_update.html'
    model = User
    form_class = forms.UserPublicKeyForm
    success_url = reverse_lazy('users:user-profile')

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Users'),
            'action': _('Public key update'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserPublicKeyGenerateView(LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        private, public = ssh_key_gen(username=request.user.username, hostname='jumpserver')
        request.user.public_key = public
        request.user.save()
        response = HttpResponse(private, content_type='text/plain')
        filename = "{0}-jumpserver.pem".format(request.user.username)
        response['Content-Disposition'] = 'attachment; filename={}'.format(filename)
        return response


class UserOtpEnableAuthenticationView(FormView):
    template_name = 'users/user_password_authentication.html'
    form_class = forms.UserCheckPasswordForm

    def get_form(self, form_class=None):
        user = get_user_or_tmp_user(self.request)
        form = super().get_form(form_class=form_class)
        form['username'].initial = user.username
        return form

    def get_context_data(self, **kwargs):
        user = get_user_or_tmp_user(self.request)
        context = {
            'user': user
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        user = get_user_or_tmp_user(self.request)
        password = form.cleaned_data.get('password')
        user = authenticate(username=user.username, password=password)
        if not user:
            form.add_error("password", _("Password invalid"))
            return self.form_invalid(form)
        return redirect(self.get_success_url())

    def get_success_url(self):
        return reverse('users:user-otp-enable-install-app')


class UserOtpEnableInstallAppView(TemplateView):
    template_name = 'users/user_otp_enable_install_app.html'

    def get_context_data(self, **kwargs):
        user = get_user_or_tmp_user(self.request)
        context = {
            'user': user
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class UserOtpEnableBindView(TemplateView, FormView):
    template_name = 'users/user_otp_enable_bind.html'
    form_class = forms.UserCheckOtpCodeForm
    success_url = reverse_lazy('users:user-otp-settings-success')

    def get_context_data(self, **kwargs):
        user = get_user_or_tmp_user(self.request)
        otp_uri, otp_secret_key = generate_otp_uri(self.request)
        context = {
            'otp_uri': otp_uri,
            'otp_secret_key': otp_secret_key,
            'user': user
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        otp_code = form.cleaned_data.get('otp_code')
        otp_secret_key = cache.get(self.request.session.session_key+'otp_key', '')

        if check_otp_code(otp_secret_key, otp_code):
            self.save_otp(otp_secret_key)
            return super().form_valid(form)

        else:
            form.add_error("otp_code", _("MFA code invalid, or ntp sync server time"))
            return self.form_invalid(form)

    def save_otp(self, otp_secret_key):
        user = get_user_or_tmp_user(self.request)
        user.enable_otp()
        user.otp_secret_key = otp_secret_key
        user.save()


class UserOtpDisableAuthenticationView(FormView):
    template_name = 'users/user_otp_authentication.html'
    form_class = forms.UserCheckOtpCodeForm
    success_url = reverse_lazy('users:user-otp-settings-success')

    def form_valid(self, form):
        user = self.request.user
        otp_code = form.cleaned_data.get('otp_code')
        otp_secret_key = user.otp_secret_key

        if check_otp_code(otp_secret_key, otp_code):
            user.disable_otp()
            user.save()
            return super().form_valid(form)
        else:
            form.add_error('otp_code', _('MFA code invalid, or ntp sync server time'))
            return super().form_invalid(form)


class UserOtpUpdateView(UserOtpDisableAuthenticationView):
    success_url = reverse_lazy('users:user-otp-enable-bind')


class UserOtpSettingsSuccessView(TemplateView):
    template_name = 'flash_message_standalone.html'

    # def get(self, request, *args, **kwargs):
    #     return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        title, describe = self.get_title_describe()
        context = {
            'title': title,
            'messages': describe,
            'interval': 1,
            'redirect_url': reverse('authentication:login'),
            'auto_redirect': True,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_title_describe(self):
        user = get_user_or_tmp_user(self.request)
        if self.request.user.is_authenticated:
            auth_logout(self.request)
        title = _('MFA enable success')
        describe = _('MFA enable success, return login page')
        if not user.otp_enabled:
            title = _('MFA disable success')
            describe = _('MFA disable success, return login page')

        return title, describe
