# ~*~ coding: utf-8 ~*~

from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.db.models import Q
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.detail import DetailView
from django.conf import settings

from .models import User, UserGroup, Role
from .forms import UserAddForm, UserUpdateForm, UserGroupForm


class UserListView(ListView):
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
        context.update({'path1': '用户管理', 'path2': '用户列表', 'title': '用户列表', 'keyword': self.keyword})
        return context


class UserAddView(CreateView):
    model = User
    form_class = UserAddForm
    template_name = 'users/user_add.html'
    success_url = reverse_lazy('users:user-list')

    def get_context_data(self, **kwargs):
        context = super(UserAddView, self).get_context_data(**kwargs)
        context.update({'path1': '用户管理', 'path2': '用户添加', 'title': '用户添加'})
        return context

    def form_valid(self, form):
        user = form.save()
        user.created_by = self.request.user.username or 'Admin'
        user.save()
        return super(UserAddView, self).form_valid(form)


class UserUpdateView(UpdateView):
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


class UserDeleteView(DeleteView):
    model = User
    success_url = reverse_lazy('users:user-list')
    template_name = 'users/user_delete_confirm.html'


class UserDetailView(DetailView):
    model = User
    template_name = 'users/user_detail.html'
    context_object_name = "user"

    def get_context_data(self, **kwargs):
        context = super(UserDetailView, self).get_context_data(**kwargs)
        groups = [group for group in UserGroup.objects.iterator() if group not in self.object.groups.iterator()]
        context.update({'path1': '用户管理', 'path2': '用户详情', 'title': '用户详情', 'groups': groups})
        return context


class UserGroupListView(ListView):
    model = UserGroup
    paginate_by = 20
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
        context.update({'path1': '用户管理', 'path2': '用户组列表', 'title': '用户组列表', 'keyword': self.keyword})
        return context


class UserGroupAddView(CreateView):
    model = UserGroup
    form_class = UserGroupForm
    template_name = 'users/usergroup_add.html'
    success_url = reverse_lazy('users:usergroup-list')

    def get_context_data(self, **kwargs):
        context = super(UserGroupAddView, self).get_context_data(**kwargs)
        users = User.objects.all()
        context.update({'path1': '用户管理', 'path2': '用户组添加', 'title': '用户组添加', 'users': users})
        return context

    def form_valid(self, form):
        usergroup = form.save()
        users_id_list = self.request.POST.getlist('users', [])
        users = [get_object_or_404(User, id=user_id) for user_id in users_id_list]
        usergroup.created_by = self.request.user.username or 'Admin'
        usergroup.user_set.add(*tuple(users))
        usergroup.save()
        return super(UserGroupAddView, self).form_valid(form)


class UserGroupUpdateView(UpdateView):
    pass


class UserGroupDetailView(DetailView):
    pass


class UserGroupDeleteView(DeleteView):
    pass
