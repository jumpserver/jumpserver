# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext as _
from django.conf import settings
from django.views.generic import ListView, TemplateView

from common.permissions import AdminUserRequiredMixin, LoginRequiredMixin
from common.mixins import DatetimeSearchMixin
from ..models import CommandExecution
from ..forms import CommandExecutionForm


__all__ = [
    'CommandExecutionListView', 'CommandExecutionStartView'
]


class CommandExecutionListView(AdminUserRequiredMixin, DatetimeSearchMixin, ListView):
    template_name = 'ops/command_execution_list.html'
    model = CommandExecution
    paginate_by = settings.DISPLAY_PER_PAGE
    ordering = ('-date_created',)
    context_object_name = 'task_list'
    keyword = ''

    def _get_queryset(self):
        self.keyword = self.request.GET.get('keyword', '')
        queryset = super().get_queryset()
        if self.date_from:
            queryset = queryset.filter(date_start__gte=self.date_from)
        if self.date_to:
            queryset = queryset.filter(date_start__lte=self.date_to)
        if self.keyword:
            queryset = queryset.filter(command__icontains=self.keyword)
        return queryset

    def get_queryset(self):
        queryset = self._get_queryset().filter(user=self.request.user)
        return queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Ops'),
            'action': _('Command execution list'),
            'date_from': self.date_from,
            'date_to': self.date_to,
            'keyword': self.keyword,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class CommandExecutionStartView(LoginRequiredMixin, TemplateView):
    template_name = 'ops/command_execution_create.html'
    form_class = CommandExecutionForm

    def get_user_system_users(self):
        from perms.utils import AssetPermissionUtil
        user = self.request.user
        util = AssetPermissionUtil(user)
        system_users = [s for s in util.get_system_users() if s.protocol == 'ssh']
        return system_users

    def get_context_data(self, **kwargs):
        system_users = self.get_user_system_users()
        context = {
            'app': _('Ops'),
            'action': _('Command execution'),
            'form': self.get_form(),
            'system_users': system_users
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_form(self):
        return self.form_class()
