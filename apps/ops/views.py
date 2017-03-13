# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

import json

from django.conf import settings
from django.views.generic import ListView, DetailView

from .models import TaskRecord


class TaskRecordListView(ListView):
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    model = TaskRecord
    ordering = ('-date_start',)
    context_object_name = 'task_record_list'
    template_name = 'ops/task_record_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Ops',
            'action': 'Task record list',
        }
        kwargs.update(context)
        return super(TaskRecordListView, self).get_context_data(**kwargs)


class TaskRecordDetailView(DetailView):
    model = TaskRecord
    template_name = 'ops/task_record_detail.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Ops',
            'action': 'Task record detail',
            'results': json.loads(self.object.summary),
        }
        kwargs.update(context)
        return super(TaskRecordDetailView, self).get_context_data(**kwargs)
