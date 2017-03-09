# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.conf import settings
from django.views.generic.list import ListView

from users.utils import AdminUserRequiredMixin
from .models import TaskRecord


class TaskListView(AdminUserRequiredMixin, ListView):
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    model = TaskRecord
    context_object_name = 'tasks'
    template_name = 'task/list.html'

    def get_context_data(self, **kwargs):
        context = {
            'task': 'Assets',
            'action': 'Create asset',
        }
        kwargs.update(context)
        return super(TaskListView, self).get_context_data(**kwargs)

