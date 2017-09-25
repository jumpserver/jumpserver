# -*- coding: utf-8 -*-
#
from __future__ import unicode_literals

import logging

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import ugettext as _
from django.views.generic import ListView

from .models import *

__all__ = ['TaskListView']

logger = logging.getLogger(__name__)


class TaskListView(LoginRequiredMixin, ListView):
    model = Task
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    template_name = 'devops/task_list.html'
    context_object_name = 'tasks'
    ordering = 'id'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ansible'),
            'action': _('Tasks'),
        }
        kwargs.update(context)
        return super(TaskListView, self).get_context_data(**kwargs)
