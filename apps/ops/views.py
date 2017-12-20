# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
import time
from datetime import datetime

from django.utils.translation import ugettext as _
from django.conf import settings
from django.views.generic import ListView, DetailView, View
from django.utils import timezone
from django.shortcuts import redirect, reverse

from .models import Task, AdHoc, AdHocRunHistory
from ops.tasks import rerun_task


class TaskListView(ListView):
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    model = Task
    ordering = ('-date_created',)
    context_object_name = 'task_list'
    template_name = 'ops/task_list.html'
    date_format = '%m/%d/%Y'
    keyword = date_from_s = date_to_s = ''

    def get_queryset(self):
        date_to_default = timezone.now()
        date_from_default = timezone.now() - timezone.timedelta(7)
        date_from_default_s = date_from_default.strftime(self.date_format)
        date_to_default_s = date_to_default.strftime(self.date_format)

        self.queryset = super().get_queryset()
        self.keyword = self.request.GET.get('keyword', '')
        self.date_from_s = self.request.GET.get('date_from', date_from_default_s)
        self.date_to_s = self.request.GET.get('date_to', date_to_default_s)

        if self.date_from_s:
            date_from = datetime.strptime(self.date_from_s, self.date_format)
            date_from = date_from.replace(tzinfo=timezone.get_current_timezone())
            self.queryset = self.queryset.filter(date_created__gt=date_from)

        if self.date_to_s:
            date_to = timezone.datetime.strptime(
                self.date_to_s + ' 23:59:59', '%m/%d/%Y %H:%M:%S')
            date_to = date_to.replace(tzinfo=timezone.get_current_timezone())
            self.queryset = self.queryset.filter(date_created__lt=date_to)

        if self.keyword:
            self.queryset = self.queryset.filter(
                name__icontains=self.keyword,
            )
        return self.queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Ops',
            'action': _('Task list'),
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
            'action': 'Task detail',
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class TaskAdhocView(DetailView):
    model = Task
    template_name = 'ops/task_adhoc.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Ops',
            'action': 'Task versions',
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class TaskHistoryView(DetailView):
    model = Task
    template_name = 'ops/task_history.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Ops',
            'action': 'Task run history',
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class TaskRunView(View):
    pk_url_kwarg = 'pk'

    def get(self, request, *args, **kwargs):
        pk = kwargs.get(self.pk_url_kwarg)
        rerun_task.delay(pk)
        time.sleep(0.5)
        return redirect(reverse('ops:task-detail', kwargs={'pk': pk}))


class AdHocDetailView(DetailView):
    model = AdHoc
    template_name = 'ops/adhoc_detail.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Ops',
            'action': 'Task version detail',
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdHocHistoryView(DetailView):
    model = AdHoc
    template_name = 'ops/adhoc_history.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Ops',
            'action': 'Version run history',
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdHocHistoryDetailView(DetailView):
    model = AdHocRunHistory
    template_name = 'ops/adhoc_history_detail.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Ops',
            'action': 'Run history detail',
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)