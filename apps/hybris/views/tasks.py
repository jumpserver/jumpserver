#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
from __future__ import unicode_literals
import logging
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.utils.translation import ugettext as _
from django.views.generic import ListView, RedirectView
from ..models import *

__all__ = ['TaskListView', 'DetailRedirectView']

logger = logging.getLogger(__name__)


class TaskListView(LoginRequiredMixin, ListView):
    model = TaskConfig
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    template_name = 'hybris/task_list.html'
    context_object_name = 'task_list'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Hybris'),
            'action': _('Task List'),
        }
        kwargs.update(context)
        return super(TaskListView, self).get_context_data(**kwargs)


class DetailRedirectView(LoginRequiredMixin, RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        #: 重定向url的name
        self.pattern_name = '%s:%s-%s' % ('hybris', kwargs['type'], 'detail')
        context = {
            'pk': kwargs['pk']  #: 从url中获取参数
        }
        return reverse(self.pattern_name, kwargs=context)
