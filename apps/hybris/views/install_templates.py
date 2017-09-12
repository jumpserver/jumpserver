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

__all__ = ['InstallTemplateDetailView', 'InstallTemplateUpdateView']

logger = logging.getLogger(__name__)


class InstallTemplateDetailView(LoginRequiredMixin, DetailView):
    """Install Task 的详情视图"""
    model = InstallTemplate
    template_name = 'hybris/install_template_detail.html'
    context_object_name = 'install_task'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Hybris'),
            'action': _('Install Task Detail'),

        }
        kwargs.update(context)
        return super(InstallTemplateDetailView, self).get_context_data(**kwargs)


class InstallTemplateUpdateView(LoginRequiredMixin, UpdateView):
    """Install Task 的编辑视图"""
    model = InstallTemplate
    form_class = forms.InstallUpdateForm
    template_name = 'hybris/install_template_update.html'
    context_object_name = 'task'
    success_url = reverse_lazy('hybris:templte-list')

    def get_context_data(self, **kwargs):
        context = super(InstallTemplateUpdateView, self).get_context_data(**kwargs)
        context.update({'app': _('Hybris'), 'action': _('Update Task')})
        return context
