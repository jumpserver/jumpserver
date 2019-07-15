# -*- coding: utf-8 -*-
#

from django.views.generic import TemplateView, CreateView, \
    UpdateView, DeleteView, DetailView
from django.views.generic.detail import SingleObjectMixin
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse_lazy
from django.shortcuts import get_object_or_404, reverse

from common.permissions import PermissionsMixin, IsOrgAdmin
from common.const import create_success_msg, update_success_msg
from ..models import CommandFilter, CommandFilterRule, SystemUser
from ..forms import CommandFilterForm, CommandFilterRuleForm


__all__ = (
    "CommandFilterListView", "CommandFilterCreateView",
    "CommandFilterUpdateView",
    "CommandFilterRuleListView", "CommandFilterRuleCreateView",
    "CommandFilterRuleUpdateView", "CommandFilterDetailView",
)


class CommandFilterListView(PermissionsMixin, TemplateView):
    template_name = 'assets/cmd_filter_list.html'
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Command filter list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class CommandFilterCreateView(PermissionsMixin, CreateView):
    model = CommandFilter
    template_name = 'assets/cmd_filter_create_update.html'
    form_class = CommandFilterForm
    success_url = reverse_lazy('assets:cmd-filter-list')
    success_message = create_success_msg
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Create command filter'),
            'type': 'create'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class CommandFilterUpdateView(PermissionsMixin, UpdateView):
    model = CommandFilter
    template_name = 'assets/cmd_filter_create_update.html'
    form_class = CommandFilterForm
    success_url = reverse_lazy('assets:cmd-filter-list')
    success_message = update_success_msg
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Update command filter'),
            'type': 'update'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class CommandFilterDetailView(PermissionsMixin, DetailView):
    model = CommandFilter
    template_name = 'assets/cmd_filter_detail.html'
    permission_classes = [IsOrgAdmin]

    def get_context_data(self, **kwargs):
        system_users_remain = SystemUser.objects\
            .exclude(cmd_filters=self.object)\
            .exclude(protocol='rdp')
        context = {
            'app': _('Assets'),
            'action': _('Command filter detail'),
            'system_users_remain': system_users_remain
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class CommandFilterRuleListView(PermissionsMixin, SingleObjectMixin, TemplateView):
    template_name = 'assets/cmd_filter_rule_list.html'
    model = CommandFilter
    object = None
    permission_classes = [IsOrgAdmin]

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=self.model.objects.all())
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Command filter rule list'),
            'object': self.get_object()
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class CommandFilterRuleCreateView(PermissionsMixin, CreateView):
    template_name = 'assets/cmd_filter_rule_create_update.html'
    model = CommandFilterRule
    form_class = CommandFilterRuleForm
    success_message = create_success_msg
    cmd_filter = None
    permission_classes = [IsOrgAdmin]

    def get_success_url(self):
        return reverse('assets:cmd-filter-rule-list', kwargs={
            'pk': self.cmd_filter.id
        })

    def get_form(self, form_class=None):
        form = super().get_form(form_class=form_class)
        form['filter'].initial = self.cmd_filter
        form['filter'].field.widget.attrs['readonly'] = 1
        return form

    def dispatch(self, request, *args, **kwargs):
        filter_pk = self.kwargs.get('filter_pk')
        self.cmd_filter = get_object_or_404(CommandFilter, pk=filter_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Create command filter rule'),
            'object': self.cmd_filter,
            'request_type': 'create'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class CommandFilterRuleUpdateView(PermissionsMixin, UpdateView):
    template_name = 'assets/cmd_filter_rule_create_update.html'
    model = CommandFilterRule
    form_class = CommandFilterRuleForm
    success_message = create_success_msg
    cmd_filter = None
    permission_classes = [IsOrgAdmin]

    def get_success_url(self):
        return reverse('assets:cmd-filter-rule-list', kwargs={
            'pk': self.cmd_filter.id
        })

    def get_form(self, form_class=None):
        form = super().get_form(form_class=form_class)
        form['filter'].initial = self.cmd_filter
        form['filter'].field.widget.attrs['readonly'] = 1
        return form

    def dispatch(self, request, *args, **kwargs):
        filter_pk = self.kwargs.get('filter_pk')
        self.cmd_filter = get_object_or_404(CommandFilter, pk=filter_pk)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Update command filter rule'),
            'object': self.cmd_filter,
            'rule': self.get_object(),
            'request_type': 'update'
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)