# -*- coding: utf-8 -*-
#

from django.views.generic import TemplateView, CreateView, \
    UpdateView, DeleteView, DetailView
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse_lazy

from common.permissions import PermissionsMixin, IsOrgAdmin
from common.const import create_success_msg, update_success_msg
from ..models import Label
from ..forms import LabelForm


__all__ = (
    "LabelListView", "LabelCreateView", "LabelUpdateView",
    "LabelDetailView", "LabelDeleteView",
)


class LabelListView(PermissionsMixin, TemplateView):
    template_name = 'assets/label_list.html'
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Label list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class LabelCreateView(PermissionsMixin, CreateView):
    model = Label
    template_name = 'assets/label_create_update.html'
    form_class = LabelForm
    success_url = reverse_lazy('assets:label-list')
    success_message = create_success_msg
    disable_name = ['draw', 'search', 'limit', 'offset', '_']
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Create label'),
            'type': 'create'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def form_valid(self, form):
        name = form.cleaned_data.get('name')
        if name in self.disable_name:
            msg = _(
                'Tips: Avoid using label names reserved internally: {}'
            ).format(', '.join(self.disable_name))
            form.add_error("name", msg)
            return self.form_invalid(form)
        return super().form_valid(form)


class LabelUpdateView(PermissionsMixin, UpdateView):
    model = Label
    template_name = 'assets/label_create_update.html'
    form_class = LabelForm
    success_url = reverse_lazy('assets:label-list')
    success_message = update_success_msg
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Update label'),
            'type': 'update'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class LabelDetailView(PermissionsMixin, DetailView):
    pass


class LabelDeleteView(PermissionsMixin, DeleteView):
    model = Label
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('assets:label-list')
    permission_classes = [IsOrgAdmin]
