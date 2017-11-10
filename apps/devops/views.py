# -*- coding: utf-8 -*-
#
from __future__ import unicode_literals

import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import ugettext as _
from django.views.generic import TemplateView, DetailView

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
