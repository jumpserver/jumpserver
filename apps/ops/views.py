# ~*~ coding: utf-8 ~*~

from django.utils.translation import ugettext as _
from django.conf import settings
from django.views.generic import ListView, DetailView, TemplateView

from common.mixins import DatetimeSearchMixin
from .models import Task, AdHoc, AdHocRunHistory, CeleryTask
from common.permissions import SuperUserRequiredMixin


class TaskListView(SuperUserRequiredMixin, DatetimeSearchMixin, ListView):
    paginate_by = settings.DISPLAY_PER_PAGE
    model = Task
    ordering = ('-date_created',)
    context_object_name = 'task_list'
    template_name = 'ops/task_list.html'
    keyword = ''

    def get_queryset(self):
        self.queryset = super().get_queryset()
        self.keyword = self.request.GET.get('keyword', '')
        self.queryset = self.queryset.filter(
            date_created__gt=self.date_from,
            date_created__lt=self.date_to
        )

        if self.keyword:
            self.queryset = self.queryset.filter(
                name__icontains=self.keyword,
            )
        return self.queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Task list'),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'keyword': self.keyword,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class TaskDetailView(SuperUserRequiredMixin, DetailView):
    model = Task
    template_name = 'ops/task_detail.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Task detail'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class TaskAdhocView(SuperUserRequiredMixin, DetailView):
    model = Task
    template_name = 'ops/task_adhoc.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Task versions'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class TaskHistoryView(SuperUserRequiredMixin, DetailView):
    model = Task
    template_name = 'ops/task_history.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Task run history'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdHocDetailView(SuperUserRequiredMixin, DetailView):
    model = AdHoc
    template_name = 'ops/adhoc_detail.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': 'Task version detail',
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdHocHistoryView(SuperUserRequiredMixin, DetailView):
    model = AdHoc
    template_name = 'ops/adhoc_history.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Version run history'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdHocHistoryDetailView(SuperUserRequiredMixin, DetailView):
    model = AdHocRunHistory
    template_name = 'ops/adhoc_history_detail.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Run history detail'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class CeleryTaskLogView(SuperUserRequiredMixin, DetailView):
    template_name = 'ops/celery_task_log.html'
    model = CeleryTask
