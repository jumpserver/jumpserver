# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals
from django import forms
from django.shortcuts import reverse, redirect
from django.utils.translation import ugettext as _
from django.urls import reverse_lazy
from django.views.generic import ListView
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView, UpdateView, FormMixin
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.contrib.messages.views import SuccessMessageMixin

from common.utils import get_logger
from perms.models import AssetPermission
from ..models import User, UserGroup
from ..utils import AdminUserRequiredMixin
from .. import forms

__all__ = ['UserGroupListView', 'UserGroupCreateView', 'UserGroupDetailView',
           'UserGroupUpdateView', 'UserGroupAssetPermissionCreateView',
           'UserGroupAssetPermissionView', 'UserGroupGrantedAssetView']
logger = get_logger(__name__)


class UserGroupListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'users/user_group_list.html'

    def get_context_data(self, **kwargs):
        context = super(UserGroupListView, self).get_context_data(**kwargs)
        context.update({'app': _('Users'), 'action': _('User group list')})
        return context


class UserGroupCreateView(AdminUserRequiredMixin, SuccessMessageMixin, CreateView):
    model = UserGroup
    form_class = forms.UserGroupForm
    template_name = 'users/user_group_create_update.html'
    success_url = reverse_lazy('users:user-group-list')
    success_message = '<a href={url}> {name} </a> was created successfully'

    def get_context_data(self, **kwargs):
        context = super(UserGroupCreateView, self).get_context_data(**kwargs)
        users = User.objects.all()
        context.update({'app': _('Users'), 'action': _('Create user group'),
                        'users': users})
        return context

    # 需要添加组下用户, 而user并不是group的多对多,所以需要手动建立关系
    def form_valid(self, form):
        user_group = form.save()
        users_id_list = self.request.POST.getlist('users', [])
        users = User.objects.filter(id__in=users_id_list)
        user_group.created_by = self.request.user.username or 'Admin'
        user_group.users.add(*users)
        user_group.save()
        return super(UserGroupCreateView, self).form_valid(form)

    def get_success_message(self, cleaned_data):
        url = reverse_lazy('users:user-group-detail',
                           kwargs={'pk': self.object.id}
                           )
        return self.success_message.format(
            url=url, name=self.object.name
        )


class UserGroupUpdateView(AdminUserRequiredMixin, UpdateView):
    model = UserGroup
    form_class = forms.UserGroupForm
    template_name = 'users/user_group_create_update.html'
    success_url = reverse_lazy('users:user-group-list')

    def get_context_data(self, **kwargs):
        # self.object = self.get_object()
        context = super(UserGroupUpdateView, self).get_context_data(**kwargs)
        users = User.objects.all()
        group_users = [user.id for user in self.object.users.all()]
        context.update({
            'app': _('Users'),
            'action': _('Update user group'),
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
    context_object_name = 'user_group'
    template_name = 'users/user_group_detail.html'

    def get_context_data(self, **kwargs):
        users = User.objects.exclude(id__in=self.object.users.all())
        context = {
            'app': _('Users'),
            'action': _('User group detail'),
            'users': users,
        }
        kwargs.update(context)
        return super(UserGroupDetailView, self).get_context_data(**kwargs)


class UserGroupAssetPermissionView(AdminUserRequiredMixin, FormMixin,
                                   SingleObjectMixin, ListView):
    model = UserGroup
    template_name = 'users/user_group_asset_permission.html'
    context_object_name = 'user_group'
    form_class = forms.UserPrivateAssetPermissionForm

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=UserGroup.objects.all())
        return super(UserGroupAssetPermissionView, self)\
            .get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Users',
            'action': 'User group asset permissions',
        }
        kwargs.update(context)
        return super(UserGroupAssetPermissionView, self)\
            .get_context_data(**kwargs)


class UserGroupAssetPermissionCreateView(AdminUserRequiredMixin, CreateView):
    form_class = forms.UserGroupPrivateAssetPermissionForm
    model = AssetPermission

    def get(self, request, *args, **kwargs):
        user_group = self.get_object(queryset=UserGroup.objects.all())
        return redirect(reverse('users:user-group-asset-permission',
                                kwargs={'pk': user_group.id}))

    def post(self, request, *args, **kwargs):
        self.user_group = self.get_object(queryset=UserGroup.objects.all())
        return super(UserGroupAssetPermissionCreateView, self)\
            .post(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form = super(UserGroupAssetPermissionCreateView, self)\
            .get_form(form_class=form_class)
        form.user_group = self.user_group
        return form

    def form_invalid(self, form):
        return redirect(reverse('users:user-group-asset-permission',
                                kwargs={'pk': self.user_group.id}))

    def get_success_url(self):
        return reverse('users:user-group-asset-permission',
                       kwargs={'pk': self.user_group.id})


class UserGroupGrantedAssetView(AdminUserRequiredMixin, DetailView):
    model = User
    template_name = 'users/user_group_granted_asset.html'
    context_object_name = 'user_group'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=UserGroup.objects.all())
        return super(UserGroupGrantedAssetView, self)\
            .get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {
            'app': 'User',
            'action': 'User group granted asset',
        }
        kwargs.update(context)
        return super(UserGroupGrantedAssetView, self).get_context_data(**kwargs)
