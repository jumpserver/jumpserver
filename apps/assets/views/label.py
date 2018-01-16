# -*- coding: utf-8 -*-
#

from django.views.generic import ListView, TemplateView, CreateView, \
    UpdateView, DeleteView, DetailView
from django.utils.translation import ugettext_lazy as _


from common.mixins import AdminUserRequiredMixin


__all__ = (
    "LabelListView", "LabelCreateView", "LabelUpdateView",
    "LabelDetailView", "LabelDeleteView",
)


class LabelListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'assets/label_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Label list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class LabelCreateView(AdminUserRequiredMixin, CreateView):
    pass


class LabelUpdateView(AdminUserRequiredMixin, UpdateView):
    pass


class LabelDetailView(AdminUserRequiredMixin, DetailView):
    pass


class LabelDeleteView(AdminUserRequiredMixin, DeleteView):
    pass
