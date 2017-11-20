# -*- coding: utf-8 -*-
#
from __future__ import unicode_literals

import json
import logging
from datetime import datetime
from django.utils import timezone

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, DetailView,ListView

from django.conf import settings
from .forms import TaskForm
from .models import *
from .hands import *

logger = logging.getLogger(__name__)


class TaskListView(LoginRequiredMixin, TemplateView):
    template_name = 'devops/task_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ansible'),
            'action': _('Tasks'),
        }
        kwargs.update(context)
        return super(TaskListView, self).get_context_data(**kwargs)


class TaskCreateView(AdminUserRequiredMixin, TemplateView):
    template_name = 'devops/task_create.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ansible'),
            'action': _('Create Task'),
            'form': TaskForm,
        }
        kwargs.update(context)
        return super(TaskCreateView, self).get_context_data(**kwargs)


class TaskUpdateView(AdminUserRequiredMixin, TemplateView):
    template_name = 'devops/task_update.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ansible'),
            'action': _('Update Task'),
            'form': TaskForm,
            'id': kwargs['pk'],
        }
        kwargs.update(context)
        return super(TaskUpdateView, self).get_context_data(**kwargs)


class TaskDetailView(LoginRequiredMixin, DetailView):
    queryset = Task.objects.all()
    context_object_name = 'task'
    template_name = 'devops/task_detail.html'

    def get_context_data(self, **kwargs):
        assets = self.object.assets.all()
        asset_groups = self.object.groups.all()
        system_user = self.object.system_user
        print([asset for asset in Asset.objects.all()
               if asset not in assets])
        context = {
            'app': _('Ansible'),
            'action': _('Task Detail'),
            'assets': assets,
            'assets_remain': [asset for asset in Asset.objects.all()
                              if asset not in assets],
            'asset_groups': asset_groups,
            'asset_groups_remain': [asset_group for asset_group in AssetGroup.objects.all()
                                    if asset_group not in asset_groups],
            'system_user': system_user,
            'system_users_remain': SystemUser.objects.exclude(
                id=system_user.id) if system_user else SystemUser.objects.all(),
        }
        kwargs.update(context)
        return super(TaskDetailView, self).get_context_data(**kwargs)


class RecordListView(ListView):
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    model = Record
    ordering = ('-date_start',)
    context_object_name = 'task_list'
    template_name = 'devops/record_list.html'
    date_format = '%m/%d/%Y'
    keyword = date_from_s = date_to_s = ''

    def get_queryset(self):
        date_now = timezone.localtime(timezone.now())
        date_to_default = date_now.strftime(self.date_format)
        date_from_default = (date_now - timezone.timedelta(7)) \
            .strftime(self.date_format)

        self.queryset = super(RecordListView, self).get_queryset()
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
            'app': 'Ansible',
            'action': 'Task record list',
            'date_from': self.date_from_s,
            'date_to': self.date_to_s,
            'keyword': self.keyword,
        }
        kwargs.update(context)
        return super(RecordListView, self).get_context_data(**kwargs)


class RecordDetailView(DetailView):
    model = Record
    template_name = 'devops/record_detail.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Ansible',
            'action': 'Task record detail',
            'results': json.loads(self.object.summary or '{}'),
        }
        kwargs.update(context)
        return super(RecordDetailView, self).get_context_data(**kwargs)
