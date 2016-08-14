# ~*~ coding: utf-8 ~*~

from django.views.generic.list import ListView
from django.views.generic.edit import CreateView

from .models import User, UserGroup
from .forms import UserForm


class UserListView(ListView):
    model = User
    paginate_by = 10
    context_object_name = 'user_list'
    template_name = 'users/user_list.html'

    def get_context_data(self, **kwargs):
        context = super(UserListView, self).get_context_data(**kwargs)
        context.update({'path1': '用户管理', 'path2': '用户列表', 'title': '用户列表'})
        return context


class UserAddView(CreateView):
    model = User
    form_class = UserForm
    template_name = 'users/user_add.html'

