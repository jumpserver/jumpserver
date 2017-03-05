# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.conf import settings
from django.views.generic.list import ListView, MultipleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.detail import DetailView, SingleObjectMixin

from users.utils import AdminUserRequiredMixin
from ops.utils.mixins import CreateSudoPrivilegesMixin, ListSudoPrivilegesMixin
from .models import Task


class TaskListView(AdminUserRequiredMixin, ListView):
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    model = Task
    context_object_name = 'tasks'
    template_name = 'task/list.html'

    def get_context_data(self, **kwargs):
        context = {
            'task': 'Assets',
            'action': 'Create asset',
        }
        kwargs.update(context)
        return super(TaskListView, self).get_context_data(**kwargs)


class TaskCreateView(AdminUserRequiredMixin, CreateView):
    model = Task
    template_name = 'task/create.html'


class TaskUpdateView(AdminUserRequiredMixin, UpdateView):
    model = Task
    template_name = 'task/update.html'


class TaskDetailView(DetailView):
    model = Task
    context_object_name = 'task'
    template_name = 'task/detail.html'
