# ~*~ coding: utf-8 ~*~

from django.urls import reverse_lazy
from django.db.models import Q
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from .models import User, UserGroup, Role
from .forms import UserForm


class UserListView(ListView):
    model = User
    paginate_by = 10
    context_object_name = 'user_list'
    template_name = 'users/user_list.html'
    ordering = '-date_joined'

    def get_queryset(self):
        self.queryset = super(UserListView, self).get_queryset()
        self.keyword = keyword = self.request.GET.get('keyword', '')
        if keyword:
            self.queryset = self.queryset.filter(Q(username__icontains=keyword) |
                                                 Q(name__icontains=keyword))
        return self.queryset

    def get_context_data(self, **kwargs):
        context = super(UserListView, self).get_context_data(**kwargs)
        context.update({'path1': '用户管理', 'path2': '用户列表', 'title': '用户列表', 'keyword': self.keyword})
        return context


class UserAddView(CreateView):
    model = User
    form_class = UserForm
    initial = {'role': Role.objects.get(name='User')}
    template_name = 'users/user_add.html'
    success_url = reverse_lazy('users:user-list')

    def get_context_data(self, **kwargs):
        context = super(UserAddView, self).get_context_data(**kwargs)
        context.update({'path1': '用户管理', 'path2': '用户添加', 'title': '用户添加'})
        return context

    def form_valid(self, form):
        user = form.save()
        password = form['password'].value()
        user.set_password(password)
        return super(UserAddView, self).form_valid(form)


class UserUpdateView(UpdateView):
    model = User
    form_class = UserForm
    template_name = 'users/user_edit.html'
    success_url = reverse_lazy('users:user-list')

    def form_valid(self, form):
        user = form.save()
        password = form['password'].value()
        if password:
            user.set_password(password)
        return super(UserUpdateView, self).form_valid(form)
