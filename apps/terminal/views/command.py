# -*- coding: utf-8 -*-
#

from django.views.generic import ListView, View
from django.conf import settings
from django.utils.translation import ugettext as _
from django.http import HttpResponse
from django.template import loader
import time

from common.mixins import DatetimeSearchMixin
from common.permissions import AdminUserRequiredMixin
from ..models import Command
from .. import utils
from ..backends import get_multi_command_storage

__all__ = ['CommandListView', 'CommandExportView']
common_storage = get_multi_command_storage()


class CommandListView(DatetimeSearchMixin, AdminUserRequiredMixin, ListView):
    model = Command
    template_name = "terminal/command_list.html"
    context_object_name = 'command_list'
    paginate_by = settings.DISPLAY_PER_PAGE
    command = user = asset = system_user = ""
    date_from = date_to = None

    def get_queryset(self):
        self.command = self.request.GET.get('command', '')
        self.user = self.request.GET.get("user", '')
        self.asset = self.request.GET.get('asset', '')
        self.system_user = self.request.GET.get('system_user', '')
        filter_kwargs = dict()
        filter_kwargs['date_from'] = self.date_from
        filter_kwargs['date_to'] = self.date_to
        if self.user:
            filter_kwargs['user'] = self.user
        if self.asset:
            filter_kwargs['asset'] = self.asset
        if self.system_user:
            filter_kwargs['system_user'] = self.system_user
        if self.command:
            filter_kwargs['input'] = self.command
        queryset = common_storage.filter(**filter_kwargs)
        return queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Terminal'),
            'action': _('Command list'),
            'user_list': utils.get_session_user_list(),
            'asset_list': utils.get_session_asset_list(),
            'system_user_list': utils.get_session_system_user_list(),
            'command': self.command,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'user': self.user,
            'asset': self.asset,
            'system_user': self.system_user,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class CommandExportView(DatetimeSearchMixin, AdminUserRequiredMixin, View):
    model = Command
    command = user = asset = system_user = action = ''
    date_from = date_to = None

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        template = 'terminal/command_report.html'
        context = {
            'queryset': queryset,
            'total_count': len(queryset),
            'now': time.time(),
        }
        content = loader.render_to_string(template, context, request)
        content_type = 'application/octet-stream'
        response = HttpResponse(content, content_type)
        filename = 'command-report-{}.html'.format(int(time.time()))
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        return response

    def get_queryset(self):
        self.get_date_range()
        self.action = self.request.GET.get('action', '')
        self.command = self.request.GET.get('command', '')
        self.user = self.request.GET.get("user", '')
        self.asset = self.request.GET.get('asset', '')
        self.system_user = self.request.GET.get('system_user', '')
        filter_kwargs = dict()
        filter_kwargs['date_from'] = self.date_from
        filter_kwargs['date_to'] = self.date_to
        if self.user:
            filter_kwargs['user'] = self.user
        if self.asset:
            filter_kwargs['asset'] = self.asset
        if self.system_user:
            filter_kwargs['system_user'] = self.system_user
        if self.command:
            filter_kwargs['input'] = self.command
        queryset = common_storage.filter(**filter_kwargs)
        return queryset
