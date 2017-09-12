#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
from __future__ import unicode_literals
import logging
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils.translation import ugettext as _
from django.views.generic import DetailView, UpdateView
from ..models import *
from .. import forms

__all__ = ['InstallDetailView', 'InstallUpdateView']

logger = logging.getLogger(__name__)


class InstallDetailView(LoginRequiredMixin, DetailView):
    """Install Task 的详情视图"""
    model = InstallConfig
    template_name = 'hybris/install_task_detail.html'
    context_object_name = 'install_task'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Hybris'),
            'action': _('Install Task Detail'),

        }
        kwargs.update(context)
        return super(InstallDetailView, self).get_context_data(**kwargs)


class InstallUpdateView(LoginRequiredMixin, UpdateView):
    """Install Task 的编辑视图"""
    model = InstallConfig
    form_class = forms.InstallUpdateForm
    template_name = 'hybris/install_task_update.html'
    context_object_name = 'task'
    success_url = reverse_lazy('hybris:task-list')

    def form_valid(self, form):
        # username = self.object.username
        # user = form.save(commit=False)
        # user.username = username
        # user.save()
        # password = self.request.POST.get('password', '')
        # if password:
        #     user.set_password(password)
        return super(InstallUpdateView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(InstallUpdateView, self).get_context_data(**kwargs)
        context.update({'app': _('Hybris'), 'action': _('Update Task')})
        return context
