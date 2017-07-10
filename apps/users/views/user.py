# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals

import json
import uuid
import csv
import codecs
from io import StringIO

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.utils.translation import ugettext as _
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import ListView
from django.views.generic.base import TemplateView
from django.views.generic.edit import (
    CreateView, UpdateView, FormMixin, FormView
)
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import logout as auth_logout

from .. import forms
from ..models import User, UserGroup
from ..utils import AdminUserRequiredMixin, user_add_success_next
from common.mixins import JSONResponseMixin
from common.utils import get_logger, get_object_or_none
from perms.models import AssetPermission

__all__ = [
    'UserListView', 'UserCreateView', 'UserDetailView',
    'UserUpdateView', 'UserAssetPermissionCreateView',
    'UserAssetPermissionView', 'UserGrantedAssetView',
    'UserExportView',  'UserBulkImportView', 'UserProfileView',
    'UserProfileUpdateView', 'UserPasswordUpdateView',
    'UserPublicKeyUpdateView', 'UserBulkUpdateView',
]

logger = get_logger(__name__)


class UserListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'users/user_list.html'

    def get_context_data(self, **kwargs):
        context = super(UserListView, self).get_context_data(**kwargs)
        context.update({
            'app': _('Users'),
            'action': _('User list'),
        })
        return context


class UserCreateView(AdminUserRequiredMixin, SuccessMessageMixin, CreateView):
    model = User
    form_class = forms.UserCreateUpdateForm
    template_name = 'users/user_create.html'
    success_url = reverse_lazy('users:user-list')
    success_message = _('Create user <a href="{url}">{name}</a> successfully.')

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
        url = reverse_lazy('users:user-detail', kwargs={'pk': self.object.pk})
        return self.success_message.format(
            url=url, name=self.object.name
        )


class UserUpdateView(AdminUserRequiredMixin, UpdateView):
    model = User
    form_class = forms.UserCreateUpdateForm
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


class UserBulkUpdateView(AdminUserRequiredMixin, ListView):
    model = User
    form_class = forms.UserBulkUpdateForm
    template_name = 'users/user_bulk_update.html'
    success_url = reverse_lazy('users:user-list')

    def get(self, request, *args, **kwargs):
        users_id = self.request.GET.get('users_id', '')
        self.id_list = [int(i) for i in users_id.split(',') if i.isdigit()]

        if kwargs.get('form'):
            self.form = kwargs['form']
        elif users_id:
            self.form = self.form_class(
                initial={'users': self.id_list}
            )
        else:
            self.form = self.form_class()
        return super(UserBulkUpdateView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            form.save()
            return redirect(self.success_url)
        else:
            return self.get(request, form=form, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Assets',
            'action': 'Bulk update asset',
            'form': self.form,
            'users_selected': self.id_list,
            'users': User.objects.all(),
        }
        kwargs.update(context)
        return super(UserBulkUpdateView, self).get_context_data(**kwargs)


class UserDetailView(AdminUserRequiredMixin, DetailView):
    model = User
    template_name = 'users/user_detail.html'
    context_object_name = "user_object"

    def get_context_data(self, **kwargs):
        groups = UserGroup.objects.exclude(id__in=self.object.groups.all())
        context = {
            'app': _('Users'),
            'action': _('User detail'),
            'groups': groups
        }
        kwargs.update(context)
        return super(UserDetailView, self).get_context_data(**kwargs)


# USER_ATTR_MAPPING = (
#     ('name', 'Name'),
#     ('username', 'Username'),
#     ('email', 'Email'),
#     ('groups', 'User groups'),
#     ('role', 'Role'),
#     ('phone', 'Phone'),
#     ('wechat', 'Wechat'),
#     ('comment', 'Comment'),
# )


@method_decorator(csrf_exempt, name='dispatch')
class UserExportView(View):
    def get(self, request):
        fields = [
            User._meta.get_field(name)
            for name in [
                'id', 'name', 'username', 'email', 'role', 'wechat', 'phone',
                'enable_otp', 'is_active', 'comment',
            ]
        ]
        spm = request.GET.get('spm', '')
        users_id = cache.get(spm, ['1'])
        filename = 'users-{}.csv'.format(
            timezone.localtime(timezone.now()).strftime('%Y-%m-%d_%H-%M-%S'))
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

    def form_valid(self, form):
        file = form.cleaned_data['file']
        data = file.read().decode('utf-8').strip(codecs.BOM_UTF8.decode('utf-8'))
        csv_file = StringIO(data)
        reader = csv.reader(csv_file)
        csv_data = [row for row in reader]
        header_ = csv_data[0]
        fields = [
            User._meta.get_field(name)
            for name in [
                'id', 'name', 'username', 'email', 'role', 'wechat', 'phone',
                'enable_otp', 'is_active', 'comment',
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
            id_ = user_dict.pop('id', 0)
            user = get_object_or_none(User, id=id_)
            for k, v in user_dict.items():
                if k in ['enable_otp', 'is_active']:
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

            if not user:
                try:
                    groups = user_dict.pop('groups')
                    user = User.objects.create(**user_dict)
                    user.groups.set(groups)
                    created.append(user_dict['username'])
                    user_add_success_next(user)
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


class UserAssetPermissionView(AdminUserRequiredMixin, FormMixin,
                              SingleObjectMixin, ListView):
    model = User
    template_name = 'users/user_asset_permission.html'
    context_object_name = 'user'
    form_class = forms.UserPrivateAssetPermissionForm

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=User.objects.all())
        return super(UserAssetPermissionView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Users',
            'action': 'User asset permissions',
        }
        kwargs.update(context)
        return super(UserAssetPermissionView, self).get_context_data(**kwargs)


class UserAssetPermissionCreateView(AdminUserRequiredMixin, CreateView):
    form_class = forms.UserPrivateAssetPermissionForm
    model = AssetPermission

    def get(self, request, *args, **kwargs):
        user = self.get_object(queryset=User.objects.all())
        return redirect(reverse('users:user-asset-permission',
                                kwargs={'pk': user.id}))

    def post(self, request, *args, **kwargs):
        self.user = self.get_object(queryset=User.objects.all())
        return super(UserAssetPermissionCreateView, self)\
            .post(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super(UserAssetPermissionCreateView, self)\
            .get_form(form_class=form_class)
        form.user = self.user
        return form

    def form_invalid(self, form):
        return redirect(reverse('users:user-asset-permission',
                                kwargs={'pk': self.user.id}))

    def get_success_url(self):
        return reverse('users:user-asset-permission',
                       kwargs={'pk': self.user.id})


class UserGrantedAssetView(AdminUserRequiredMixin, DetailView):
    model = User
    template_name = 'users/user_granted_asset.html'
    context_object_name = 'user'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=User.objects.all())
        return super(UserGrantedAssetView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {
            'app': 'User',
            'action': 'User granted asset',
        }
        kwargs.update(context)
        return super(UserGrantedAssetView, self).get_context_data(**kwargs)


class UserProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'users/user_profile.html'

    def get_context_data(self, **kwargs):
        from perms.utils import get_user_granted_assets
        assets = get_user_granted_assets(self.request.user)
        context = {
            'app': 'User',
            'action': 'User Profile',
            'assets': assets,
        }
        kwargs.update(context)
        return super(UserProfileView, self).get_context_data(**kwargs)


class UserProfileUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'users/user_profile_update.html'
    model = User
    form_class = forms.UserProfileForm
    success_url = reverse_lazy('users:user-profile')
    success_message = _('Create user <a href="{url}">{name}</a> successfully.')

    def get_object(self, queryset=None):
        return self.request.user

    def get_success_message(self, cleaned_data):
        url = reverse_lazy('users:user-detail', kwargs={'pk': self.object.pk})
        return self.success_message.format(
            url=url, name=self.object.name
        )

    def get_context_data(self, **kwargs):
        context = {
            'app': 'User',
            'action': 'Profile update',
        }
        kwargs.update(context)
        return super(UserProfileUpdateView, self).get_context_data(**kwargs)


class UserPasswordUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'users/user_password_update.html'
    model = User
    form_class = forms.UserPasswordForm
    success_url = reverse_lazy('users:user-profile')

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = {
            'app': 'User',
            'action': 'Password update',
        }
        kwargs.update(context)
        return super(UserPasswordUpdateView, self).get_context_data(**kwargs)

    def get_success_url(self):
        auth_logout(self.request)
        return super(UserPasswordUpdateView, self).get_success_url()


class UserPublicKeyUpdateView(LoginRequiredMixin, UpdateView):
    template_name = 'users/user_pubkey_update.html'
    model = User
    form_class = forms.UserPublicKeyForm
    success_url = reverse_lazy('users:user-profile')

    def get_object(self, queryset=None):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = {
            'app': 'User',
            'action': 'Public key update',
        }
        kwargs.update(context)
        return super(UserPublicKeyUpdateView, self).get_context_data(**kwargs)
