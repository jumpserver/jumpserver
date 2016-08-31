# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals

import logging

from django.shortcuts import get_object_or_404, reverse, render
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.db.models import Q
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView, ProcessFormView, FormView
from django.views.generic.detail import DetailView
from django.contrib.messages.views import SuccessMessageMixin
from django.conf import settings
from django.contrib.auth import authenticate, login, logout

from .models import User, UserGroup
from .forms import UserAddForm, UserUpdateForm, UserGroupForm, UserLoginForm
from .utils import AdminUserRequiredMixin, ssh_key_gen


logger = logging.getLogger('jumpserver.users.views')


class UserLoginView(FormView):
    template_name = 'users/login.html'
    form_class = UserLoginForm
    success_url = reverse_lazy('users:user-list')

    def get(self, request, *args, **kwargs):
        if self.request.user.is_staff:
            return HttpResponseRedirect(reverse('users:user-list'))
        return super(UserLoginView, self).get(request, *args, **kwargs)

    def form_valid(self, form):
        username = form.cleaned_data.get('username', '')
        password = form.cleaned_data.get('password', '')

        user = authenticate(username=username, password=password)
        if user is not None and user.is_staff:
            login(self.request, user)
            return HttpResponseRedirect(self.success_url)

        logger.warning('Login user [%(username)s] password error' % {'username': username})
        return render(self.request, self.template_name, context={'form': form, 'error': '密码错误'})

    def form_invalid(self, form):
        logger.warning('Login form commit invalid.')
        return super(UserLoginView, self).form_invalid(form)


class UserListView(AdminUserRequiredMixin, ListView):
    model = User
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    context_object_name = 'user_list'
    template_name = 'users/user_list.html'
    ordering = '-date_joined'

    def get_queryset(self):
        self.queryset = super(UserListView, self).get_queryset()
        self.keyword = keyword = self.request.GET.get('keyword', '')
        self.sort = sort = self.request.GET.get('sort')
        if keyword:
            self.queryset = self.queryset.filter(Q(username__icontains=keyword) |
                                                 Q(name__icontains=keyword))

        if sort:
            self.queryset = self.queryset.order_by(sort)
        return self.queryset

    def get_context_data(self, **kwargs):
        context = super(UserListView, self).get_context_data(**kwargs)
        context.update({'app': '用户管理', 'action': '用户列表', 'keyword': self.keyword})
        return context


class UserAddView(AdminUserRequiredMixin, SuccessMessageMixin, CreateView):
    model = User
    form_class = UserAddForm
    template_name = 'users/user_add.html'
    success_url = reverse_lazy('users:user-list')
    success_message = '添加用户 <a href="%s">%s</a> 成功 .'

    def get_context_data(self, **kwargs):
        context = super(UserAddView, self).get_context_data(**kwargs)
        context.update({'app': '用户管理', 'action': '用户添加'})
        return context

    def form_valid(self, form):
        user = form.save(commit=False)
        user.created_by = self.request.user.username or 'System'
        user.save()
        form.save_m2m()
        return super(UserAddView, self).form_valid(form)

    def get_success_message(self, cleaned_data):
        return self.success_message % (
            reverse_lazy('users:user-detail', kwargs={'pk': self.object.pk}),
            self.object.name,
        )


class UserUpdateView(AdminUserRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'users/user_edit.html'
    context_object_name = 'user'
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

    def form_invalid(self, form):
        print(form.errors)
        return super(UserUpdateView, self).form_invalid(form)

    def get_context_data(self, **kwargs):
        context = super(UserUpdateView, self).get_context_data(**kwargs)
        context.update({'app': '用户管理', 'action': '用户编辑'})
        return context


class UserDeleteView(AdminUserRequiredMixin, DeleteView):
    model = User
    success_url = reverse_lazy('users:user-list')
    template_name = 'users/user_delete_confirm.html'


class UserDetailView(AdminUserRequiredMixin, DetailView):
    model = User
    template_name = 'users/user_detail.html'
    context_object_name = "user"

    def get_context_data(self, **kwargs):
        context = super(UserDetailView, self).get_context_data(**kwargs)
        groups = [group for group in UserGroup.objects.iterator() if group not in self.object.groups.iterator()]
        context.update({'app': '用户管理', 'action': '用户详情', 'groups': groups})
        return context


class UserGroupListView(AdminUserRequiredMixin, ListView):
    model = UserGroup
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    context_object_name = 'usergroup_list'
    template_name = 'users/usergroup_list.html'
    ordering = '-date_added'

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
        context.update({'app': '用户管理', 'action': '用户组列表', 'keyword': self.keyword})
        return context


class UserGroupAddView(AdminUserRequiredMixin, CreateView):
    model = UserGroup
    form_class = UserGroupForm
    template_name = 'users/usergroup_add.html'
    success_url = reverse_lazy('users:usergroup-list')

    def get_context_data(self, **kwargs):
        context = super(UserGroupAddView, self).get_context_data(**kwargs)
        users = User.objects.all()
        context.update({'app': '用户管理', 'action': '用户组添加', 'users': users})
        return context

    def form_valid(self, form):
        usergroup = form.save()
        users_id_list = self.request.POST.getlist('users', [])
        users = [get_object_or_404(User, id=user_id) for user_id in users_id_list]
        usergroup.created_by = self.request.user.username or 'Admin'
        usergroup.users.add(*tuple(users))
        usergroup.save()
        return super(UserGroupAddView, self).form_valid(form)


class UserGroupUpdateView(UpdateView):
    pass


class UserGroupDetailView(DetailView):
    pass


class UserGroupDeleteView(DeleteView):
    pass
