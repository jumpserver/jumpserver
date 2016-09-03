# ~*~ coding: utf-8 ~*~

from __future__ import unicode_literals

import logging

from django.shortcuts import get_object_or_404, reverse, render, Http404, redirect
from django.http import HttpResponseRedirect
from django.urls import reverse_lazy
from django.db.models import Q
from django.views.generic.base import View, TemplateView
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView, ProcessFormView, FormView
from django.views.generic.detail import DetailView
from django.contrib.messages.views import SuccessMessageMixin
from django.conf import settings
from django.http import HttpResponseRedirect
from django.contrib.auth import views as auth_view, authenticate, login, logout

from common.utils import get_object_or_none

from .models import User, UserGroup
from .forms import UserAddForm, UserUpdateForm, UserGroupForm, UserLoginForm
from .utils import AdminUserRequiredMixin, ssh_key_gen, user_add_success_next, send_reset_password_mail


logger = logging.getLogger('jumpserver.users.views')


class UserLoginView(FormView):
    template_name = 'users/login.html'
    form_class = UserLoginForm
    redirect_field_name = 'next'

    def get(self, request, *args, **kwargs):
        if self.request.user.is_staff:
            return redirect(request.POST.get(self.redirect_field_name, reverse('index')))
        # Todo: Django have bug, lose context issue: https://github.com/django/django/pull/7202
        # so we jump it and use origin method render_to_response
        # return super(UserLoginView, self).get(request, *args, **kwargs)
        return self.render_to_response(self.get_context_data(**kwargs))

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if not form.is_valid():
            return self.form_invalid(form)

        username = form['username'].value()
        password = form['password'].value()

        user = authenticate(username=username, password=password)
        if user is None:
            kwargs.update({'errors': '账号密码不正确'})
            return self.get(request, *args, **kwargs)

        login(request, user)
        return redirect(request.GET.get(self.redirect_field_name, reverse('index')))


class UserLogoutView(TemplateView):
    template_name = 'common/flash_message_standalone.html'

    def get(self, request, *args, **kwargs):
        logout(request)

        return super(UserLogoutView, self).get(request)

    def get_context_data(self, **kwargs):
        context = {
            'title': '退出登录成功',
            'messages': '退出登录成功， 返回登录页面',
            'redirect_url': reverse('users:login'),
            'auto_redirect': True,
        }
        kwargs.update(context)
        return super(UserLogoutView, self).get_context_data(**kwargs)


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

        user_add_success_next(user)

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


class UserForgetPasswordView(TemplateView):
    template_name = 'users/forget_password.html'

    def post(self, request, *args, **kwargs):
        email = request.POST.get('email')
        user = get_object_or_none(User, email=email)
        if not user:
            return self.get(request, errors='邮件地址错误,请重新输入')
        else:
            send_reset_password_mail(user)
            return HttpResponseRedirect(reverse('users:forget-password-sendmail-success'))


class UserForgetPasswordSendmailSuccessView(TemplateView):
    template_name = 'common/flash_message_standalone.html'

    def get_context_data(self, **kwargs):
        context = {
            'title': '发送重置邮件',
            'messages': '发送重置邮件成功, 请登录邮箱查看, 按照提示操作 (如果没收到,请等待3-5分钟)',
            'redirect_url': reverse('users:login'),
        }
        kwargs.update(context)
        return super(UserForgetPasswordSendmailSuccessView, self).get_context_data(**kwargs)


class UserResetPasswordSuccessView(TemplateView):
    template_name = 'common/flash_message_standalone.html'

    def get_context_data(self, **kwargs):
        context = {
            'title': '重设密码成功',
            'messages': '密码重置成功, 返回登录页面 ',
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
            kwargs.update({'errors': 'Token不正确或已过期'})
        return super(UserResetPasswordView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        password = request.POST.get('password')
        password_confirm = request.POST.get('password-confirm')
        token = request.GET.get('token')

        if password != password_confirm:
            return self.get(request, errors='两次密码不一致')

        user = User.validate_reset_token(token)
        if not user:
            return self.get(request, errors='Token不正确或已过期')

        user.reset_password(password)
        return HttpResponseRedirect(reverse('users:reset-password-success'))
