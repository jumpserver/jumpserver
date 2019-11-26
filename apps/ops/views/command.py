# -*- coding: utf-8 -*-
#

from django.utils.translation import ugettext as _
from django.conf import settings
from django.views.generic import ListView, TemplateView

from common.permissions import (
    PermissionsMixin, IsOrgAdmin,  IsValidUser, IsOrgAuditor
)
from common.mixins import DatetimeSearchMixin
from orgs.utils import tmp_to_root_org
from ..models import CommandExecution
from ..forms import CommandExecutionForm


__all__ = [
    'CommandExecutionListView', 'CommandExecutionStartView'
]


class CommandExecutionListView(PermissionsMixin, DatetimeSearchMixin, ListView):
    template_name = 'ops/command_execution_list.html'
    model = CommandExecution
    paginate_by = settings.DISPLAY_PER_PAGE
    ordering = ('-date_created',)
    context_object_name = 'task_list'
    keyword = ''
    permission_classes = [IsOrgAdmin | IsOrgAuditor]

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


class CommandExecutionStartView(PermissionsMixin, TemplateView):
    template_name = 'ops/command_execution_create.html'
    form_class = CommandExecutionForm
    permission_classes = [IsValidUser]

    def get_permissions(self):
        if not settings.SECURITY_COMMAND_EXECUTION:
            return [IsOrgAdmin]
        return super().get_permissions()

    def get_user_system_users(self):
        from perms.utils import AssetPermissionUtilV2
        user = self.request.user
        with tmp_to_root_org():
            util = AssetPermissionUtilV2(user)
            system_users = util.get_system_users()
        return system_users

    def get_context_data(self, **kwargs):
        system_users = self.get_user_system_users()
        context = {
            'app': _('Ops'),
            'action': _('Command execution'),
            'form': self.get_form(),
            'system_users': system_users,
            'ws_port': settings.WS_LISTEN_PORT
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

    def get_form(self):
        return self.form_class()
