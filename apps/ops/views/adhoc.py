# ~*~ coding: utf-8 ~*~

from django.utils.translation import ugettext as _
from django.conf import settings
from django.views.generic import ListView, DetailView, TemplateView

from common.mixins import DatetimeSearchMixin
from common.permissions import PermissionsMixin, IsOrgAdmin
from orgs.utils import current_org
from ..models import Task, AdHoc, AdHocRunHistory


__all__ = [
    'TaskListView', 'TaskDetailView', 'TaskHistoryView',
    'TaskAdhocView', 'AdHocDetailView', 'AdHocHistoryDetailView',
    'AdHocHistoryView'
]


class TaskListView(PermissionsMixin, TemplateView):
    paginate_by = settings.DISPLAY_PER_PAGE
    model = Task
    ordering = ('-date_created',)
    context_object_name = 'task_list'
    template_name = 'ops/task_list.html'
    keyword = ''
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Task list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class TaskDetailView(PermissionsMixin, DetailView):
    model = Task
    template_name = 'ops/task_detail.html'
    permission_classes = [IsOrgAdmin]

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


class TaskAdhocView(PermissionsMixin, DetailView):
    model = Task
    template_name = 'ops/task_adhoc.html'
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Task versions'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class TaskHistoryView(PermissionsMixin, DetailView):
    model = Task
    template_name = 'ops/task_history.html'
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Task run history'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdHocDetailView(PermissionsMixin, DetailView):
    model = AdHoc
    template_name = 'ops/adhoc_detail.html'
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': 'Task version detail',
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdHocHistoryView(PermissionsMixin, DetailView):
    model = AdHoc
    template_name = 'ops/adhoc_history.html'
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Version run history'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class AdHocHistoryDetailView(PermissionsMixin, DetailView):
    model = AdHocRunHistory
    template_name = 'ops/adhoc_history_detail.html'
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Run history detail'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)




