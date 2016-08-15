# ~*~ coding: utf-8 ~*~

from django.urls import reverse_lazy
from django.db.models import Q
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView

from .models import User, UserGroup
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
    template_name = 'users/user_add.html'
    success_url = reverse_lazy('users:user-list')

    def get_context_data(self, **kwargs):
        context = super(UserAddView, self).get_context_data(**kwargs)
        context.update({'path1': '用户管理', 'path2': '用户添加', 'title': '用户添加'})
        return context

