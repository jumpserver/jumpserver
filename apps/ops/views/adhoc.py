# ~*~ coding: utf-8 ~*~

from django.utils.translation import ugettext as _
from django.conf import settings
from django.views.generic import ListView, DetailView

from common.mixins import DatetimeSearchMixin
from common.permissions import AdminUserRequiredMixin
from orgs.utils import current_org
from ..models import Task, AdHoc, AdHocRunHistory


__all__ = [
    'TaskListView', 'TaskDetailView', 'TaskHistoryView',
    'TaskAdhocView', 'AdHocDetailView', 'AdHocHistoryDetailView',
    'AdHocHistoryView'
]


class TaskListView(AdminUserRequiredMixin, DatetimeSearchMixin, ListView):
    paginate_by = settings.DISPLAY_PER_PAGE
    model = Task
    ordering = ('-date_created',)
    context_object_name = 'task_list'
    template_name = 'ops/task_list.html'
    keyword = ''

    def get_queryset(self):
        queryset = super().get_queryset()
        if current_org.is_real():
            queryset = queryset.filter(created_by=current_org.id)
        else:
            queryset = queryset.filter(created_by='')

        self.keyword = self.request.GET.get('keyword', '')
        if self.keyword:
            queryset = queryset.filter(
                name__icontains=self.keyword,
            )
        return queryset

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


class TaskDetailView(AdminUserRequiredMixin, DetailView):
    model = Task
    template_name = 'ops/task_detail.html'

    def get_queryset(self):
        queryset = super().get_queryset()
        # Todo: 需要整理默认组织等东西
        if current_org.is_real():
            queryset = queryset.filter(created_by=current_org.id)
        else:
            queryset = queryset.filter(created_by='')
        return queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Task detail'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class TaskAdhocView(AdminUserRequiredMixin, DetailView):
    model = Task
    template_name = 'ops/task_adhoc.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Task versions'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class TaskHistoryView(AdminUserRequiredMixin, DetailView):
    model = Task
    template_name = 'ops/task_history.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Task run history'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdHocDetailView(AdminUserRequiredMixin, DetailView):
    model = AdHoc
    template_name = 'ops/adhoc_detail.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': 'Task version detail',
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdHocHistoryView(AdminUserRequiredMixin, DetailView):
    model = AdHoc
    template_name = 'ops/adhoc_history.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Version run history'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdHocHistoryDetailView(AdminUserRequiredMixin, DetailView):
    model = AdHocRunHistory
    template_name = 'ops/adhoc_history_detail.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Run history detail'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)




