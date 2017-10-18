# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
import time
import json
from datetime import datetime

from django.conf import settings
from django.views.generic import ListView, DetailView, View
from django.utils import timezone
from django.shortcuts import redirect, reverse

from .models import Task
from ops.tasks import rerun_task


class TaskListView(ListView):
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    model = Task
    ordering = ('-date_start',)
    context_object_name = 'task_list'
    template_name = 'ops/task_list.html'
    date_format = '%m/%d/%Y'
    keyword = date_from_s = date_to_s = ''

    def get_queryset(self):
        date_now = timezone.localtime(timezone.now())
        date_to_default = date_now.strftime(self.date_format)
        date_from_default = (date_now - timezone.timedelta(7)) \
            .strftime(self.date_format)

        self.queryset = super(TaskListView, self).get_queryset()
        self.keyword = self.request.GET.get('keyword', '')
        self.date_from_s = self.request.GET.get('date_from', date_from_default)
        self.date_to_s = self.request.GET.get('date_to', date_to_default)

        if self.date_from_s:
            date_from = datetime.strptime(self.date_from_s, self.date_format)
            date_from = date_from.replace(tzinfo=timezone.get_current_timezone())
            self.queryset = self.queryset.filter(date_start__gt=date_from)

        if self.date_to_s:
            date_to = timezone.datetime.strptime(
                self.date_to_s + ' 23:59:59', '%m/%d/%Y %H:%M:%S')
            date_to = date_to.replace(tzinfo=timezone.get_current_timezone())
            self.queryset = self.queryset.filter(date_finished__lt=date_to)

        if self.keyword:
            self.queryset = self.queryset.filter(
                name__icontains=self.keyword,
            )
        return self.queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Ops',
            'action': 'Task record list',
            'date_from': self.date_from_s,
            'date_to': self.date_to_s,
            'keyword': self.keyword,
        }
        kwargs.update(context)
        return super(TaskListView, self).get_context_data(**kwargs)


class TaskDetailView(DetailView):
    model = Task
    template_name = 'ops/task_detail.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Ops',
            'action': 'Task record detail',
            'results': json.loads(self.object.summary or '{}'),
        }
        kwargs.update(context)
        return super(TaskDetailView, self).get_context_data(**kwargs)


class TaskRunView(View):
    pk_url_kwarg = 'pk'

    def get(self, request, *args, **kwargs):
        pk = kwargs.get(self.pk_url_kwarg)
        rerun_task.delay(pk)
        time.sleep(0.5)
        return redirect(reverse('ops:task-detail', kwargs={'pk': pk}))
