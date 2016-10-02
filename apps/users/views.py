# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals

from django.conf import settings
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.files.storage import default_storage
from django.http import HttpResponseRedirect
from django.shortcuts import reverse, redirect
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.urls import reverse_lazy
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic.base import TemplateView
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView, FormView, SingleObjectMixin, \
    FormMixin
from django.views.generic.detail import DetailView

from formtools.wizard.views import SessionWizardView

from common.utils import get_object_or_none, get_logger
from .models import User, UserGroup
from .forms import UserCreateForm, UserUpdateForm, UserGroupForm, UserLoginForm, UserInfoForm, UserKeyForm, \
    UserPrivateAssetPermissionForm
from .utils import AdminUserRequiredMixin, user_add_success_next, send_reset_password_mail
from .hands import AssetPermission, get_user_granted_asset_groups, get_user_granted_assets


logger = get_logger(__name__)


@method_decorator(sensitive_post_parameters(), name='dispatch')
@method_decorator(csrf_protect, name='dispatch')
@method_decorator(never_cache, name='dispatch')
class UserLoginView(FormView):
    template_name = 'users/login.html'
    form_class = UserLoginForm
    redirect_field_name = 'next'

    def get(self, request, *args, **kwargs):
        if request.user.is_staff:
            return redirect(self.get_success_url())
        return super(UserLoginView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        auth_login(self.request, form.get_user())
        return redirect(self.get_success_url())

    def get_success_url(self):
        if self.request.user.is_first_login:
            return reverse('users:user-first-login')

        return self.request.POST.get(
            self.redirect_field_name,
            self.request.GET.get(self.redirect_field_name, reverse('index')))


@method_decorator(never_cache, name='dispatch')
class UserLogoutView(TemplateView):
    template_name = 'common/flash_message_standalone.html'

    def get(self, request, *args, **kwargs):
        auth_logout(request)
        return super(UserLogoutView, self).get(request)

    def get_context_data(self, **kwargs):
        context = {
            'title': _('Logout success'),
            'messages': _('Logout success, return login page'),
            'redirect_url': reverse('users:login'),
            'auto_redirect': True,
        }
        kwargs.update(context)
        return super(UserLogoutView, self).get_context_data(**kwargs)


class UserListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'users/user_list.html'

    def get_context_data(self, **kwargs):
        context = super(UserListView, self).get_context_data(**kwargs)
        context.update({'app': _('Users'), 'action': _('User list'), 'groups': UserGroup.objects.all()})
        return context


class UserCreateView(AdminUserRequiredMixin, SuccessMessageMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = 'users/user_create.html'
    success_url = reverse_lazy('users:user-list')
    success_message = _('Create user <a href="%s">%s</a> successfully.')

    def get_context_data(self, **kwargs):
        context = super(UserCreateView, self).get_context_data(**kwargs)
        context.update({'app': _('Users'), 'action': _('Create user')})
        return context

    def form_valid(self, form):
        user = form.save(commit=False)
        user.created_by = self.request.user.username or 'System'
        user.save()
        user_add_success_next(user)
        return super(UserCreateView, self).form_valid(form)

    def get_success_message(self, cleaned_data):
        return self.success_message % (
            reverse_lazy('users:user-detail', kwargs={'pk': self.object.pk}),
            self.object.name,
        )


class UserUpdateView(AdminUserRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'users/user_update.html'
    context_object_name = 'user_object'
    success_url = reverse_lazy('users:user-list')

    def form_valid(self, form):
        username = self.object.username
        user = form.save(commit=False)
        user.username = username
        user.save()
        password = self.request.POST.get('password', '')
        if password:
            user.set_password(password)
        return super(UserUpdateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(UserUpdateView, self).get_context_data(**kwargs)
        context.update({'app': _('Users'), 'action': _('Update user')})
        return context


class UserDetailView(AdminUserRequiredMixin, DetailView):
    model = User
    template_name = 'users/user_detail.html'
    context_object_name = "user_object"

    def get_context_data(self, **kwargs):
        groups = UserGroup.objects.exclude(id__in=self.object.groups.all())
        context = {'app': _('Users'), 'action': _('User detail'), 'groups': groups}
        kwargs.update(context)
        return super(UserDetailView, self).get_context_data(**kwargs)


class UserGroupListView(AdminUserRequiredMixin, ListView):
    model = UserGroup
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    context_object_name = 'user_group_list'
    template_name = 'users/user_group_list.html'
    ordering = '-date_created'

    def get_queryset(self):
        self.queryset = super(UserGroupListView, self).get_queryset()
        self.keyword = keyword = self.request.GET.get('keyword', '')
        self.sort = sort = self.request.GET.get('sort')
        if keyword:
            self.queryset = self.queryset.filter(name__icontains=keyword)

        if sort:
            self.queryset = self.queryset.order_by(sort)
        return self.queryset

    def get_context_data(self, **kwargs):
        context = super(UserGroupListView, self).get_context_data(**kwargs)
        context.update({'app': _('Users'), 'action': _('User group list'), 'keyword': self.keyword})
        return context


class UserGroupCreateView(AdminUserRequiredMixin, CreateView):
    model = UserGroup
    form_class = UserGroupForm
    template_name = 'users/user_group_create.html'
    success_url = reverse_lazy('users:user-group-list')

    def get_context_data(self, **kwargs):
        context = super(UserGroupCreateView, self).get_context_data(**kwargs)
        users = User.objects.all()
        context.update({'app': _('Users'), 'action': _('Create user group'), 'users': users})
        return context

    def form_valid(self, form):
        user_group = form.save()
        users_id_list = self.request.POST.getlist('users', [])
        users = User.objects.filter(id__in=users_id_list)
        user_group.created_by = self.request.user.username or 'Admin'
        user_group.users.add(*users)
        user_group.save()
        return super(UserGroupCreateView, self).form_valid(form)


class UserGroupUpdateView(AdminUserRequiredMixin, UpdateView):
    model = UserGroup
    form_class = UserGroupForm
    template_name = 'users/user_group_create.html'
    success_url = reverse_lazy('users:user-group-list')

    def get_context_data(self, **kwargs):
        self.object = self.get_object()
        context = super(UserGroupUpdateView, self).get_context_data(**kwargs)
        users = User.objects.all()
        group_users = ",".join([str(u.id) for u in self.object.users.all()])
        context.update({
            'app': _('Users'),
            'action': _('Update User Group'),
            'users': users,
            'group_users': group_users
        })
        return context

    def form_valid(self, form):
        user_group = form.save()
        users_id_list = self.request.POST.getlist('users', [])
        users = User.objects.filter(id__in=users_id_list)
        user_group.users.clear()
        user_group.users.add(*users)
        user_group.save()
        return super(UserGroupUpdateView, self).form_valid(form)


class UserGroupDetailView(AdminUserRequiredMixin, DetailView):
    model = UserGroup
    template_name = 'users/user_group_detail.html'

    def get_context_data(self, **kwargs):
        context = {'app': _('Users'), 'action': _('User Group Detail')}
        kwargs.update(context)
        return super(UserGroupDetailView, self).get_context_data(**kwargs)


class UserGroupDeleteView(DeleteView):
    pass


class UserForgotPasswordView(TemplateView):
    template_name = 'users/forgot_password.html'

    def post(self, request):
        email = request.POST.get('email')
        user = get_object_or_none(User, email=email)
        if not user:
            return self.get(request, errors=_('Email address invalid, input again'))
        else:
            send_reset_password_mail(user)
            return HttpResponseRedirect(reverse('users:forgot-password-sendmail-success'))


class UserForgotPasswordSendmailSuccessView(TemplateView):
    template_name = 'common/flash_message_standalone.html'

    def get_context_data(self, **kwargs):
        context = {
            'title': _('Send reset password message'),
            'messages': _('Send reset password mail success, login your mail box and follow it '),
            'redirect_url': reverse('users:login'),
        }
        kwargs.update(context)
        return super(UserForgotPasswordSendmailSuccessView, self).get_context_data(**kwargs)


class UserResetPasswordSuccessView(TemplateView):
    template_name = 'common/flash_message_standalone.html'

    def get_context_data(self, **kwargs):
        context = {
            'title': _('Reset password success'),
            'messages': _('Reset password success, return to login page'),
            'redirect_url': reverse('users:login'),
            'auto_redirect': True,
        }
        kwargs.update(context)
        return super(UserResetPasswordSuccessView, self).get_context_data(**kwargs)


class UserResetPasswordView(TemplateView):
    template_name = 'users/reset_password.html'

    def get(self, request, *args, **kwargs):
        token = request.GET.get('token')
        user = User.validate_reset_token(token)

        if not user:
            kwargs.update({'errors': _('Token invalid or expired')})
        return super(UserResetPasswordView, self).get(request, *args, **kwargs)

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
    form_list = [UserInfoForm, UserKeyForm]
    file_storage = default_storage

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated() and not request.user.is_first_login:
            return redirect(reverse('index'))
        return super(UserFirstLoginView, self).dispatch(request, *args, **kwargs)

    def done(self, form_list, form_dict, **kwargs):
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
        return redirect(reverse('index'))

    def get_context_data(self, **kwargs):
        context = super(UserFirstLoginView, self).get_context_data(**kwargs)
        context.update({'app': _('Users'), 'action': _('First Login')})
        return context

    def get_form_initial(self, step):
        user = self.request.user
        if step == '0':
            return {
                'name': user.name or user.username,
                'enable_otp': user.enable_otp or True,
                'wechat': user.wechat or '',
                'phone': user.phone or ''
            }
        return super(UserFirstLoginView, self).get_form_initial(step)

    def get_form(self, step=None, data=None, files=None):
        form = super(UserFirstLoginView, self).get_form(step, data, files)

        if step is None:
            step = self.steps.current

        if step == '1':
            form.user = self.request.user
        return form


class UserAssetPermissionView(AdminUserRequiredMixin, FormMixin, SingleObjectMixin, ListView):
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    template_name = 'users/user_asset_permission.html'
    context_object_name = 'user_object'
    form_class = UserPrivateAssetPermissionForm

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=User.objects.all())
        return super(UserAssetPermissionView, self).get(request, *args, **kwargs)

    def get_asset_permission_inherit_from_user_group(self):
        asset_permissions = set()
        user_groups = self.object.groups.all()

        for user_group in user_groups:
            for asset_permission in user_group.asset_permissions.all():
                setattr(asset_permission, 'is_inherit_from_user_groups', True)
                setattr(asset_permission, 'inherit_from_user_groups',
                        getattr(asset_permission, b'inherit_from_user_groups', set()).add(user_group))
                asset_permissions.add(asset_permission)
        return asset_permissions

    def get_queryset(self):
        asset_permissions = set(self.object.asset_permissions.all()) \
            | self.get_asset_permission_inherit_from_user_group()
        return list(asset_permissions)

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Users',
            'action': 'User asset permissions',
        }
        kwargs.update(context)
        return super(UserAssetPermissionView, self).get_context_data(**kwargs)


class UserAssetPermissionCreateView(AdminUserRequiredMixin, CreateView):
    form_class = UserPrivateAssetPermissionForm
    model = AssetPermission

    def get(self, request, *args, **kwargs):
        user_object = self.get_object(queryset=User.objects.all())
        return redirect(reverse('users:user-asset-permission', kwargs={'pk': user_object.id}))

    def post(self, request, *args, **kwargs):
        self.user_object = self.get_object(queryset=User.objects.all())
        return super(UserAssetPermissionCreateView, self).post(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super(UserAssetPermissionCreateView, self).get_form(form_class=form_class)
        form.user = self.user_object
        return form

    def form_invalid(self, form):
        print(form.errors)
        return redirect(reverse('users:user-asset-permission', kwargs={'pk': self.user_object.id}))

    def get_success_url(self):
        return reverse('users:user-asset-permission', kwargs={'pk': self.user_object.id})


class UserGrantedAssetView(AdminUserRequiredMixin, SingleObjectMixin, ListView):
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    template_name = 'users/user_granted_asset.html'
    context_object_name = 'user_object'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=User.objects.all())
        return super(UserGrantedAssetView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        # Convert format from {'asset': ['system_users'], ..} to
        #     [('asset', ['system_users']), ('asset', ['system_users']))
        assets_granted = [(asset, system_users) for asset, system_users in
                          get_user_granted_assets(self.object).items()]

        return assets_granted

    def get_context_data(self, **kwargs):
        asset_groups = [(asset_group, system_users) for asset_group, system_users in
                        get_user_granted_asset_groups(self.object).items()]
        context = {
            'app': 'User',
            'action': 'User granted asset',
            'asset_groups': asset_groups,
        }
        kwargs.update(context)
        return super(UserGrantedAssetView, self).get_context_data(**kwargs)
