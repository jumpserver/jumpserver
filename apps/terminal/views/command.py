# -*- coding: utf-8 -*-
#
from datetime import datetime

from django.views.generic import ListView
from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext as _

from ..models import Command
from .. import utils
from ..backends import get_command_store

__all__ = ['CommandListView']
command_store = get_command_store()


class CommandListView(ListView):
    model = Command
    template_name = "terminal/command_list.html"
    context_object_name = 'command_list'
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    command = user = asset = system_user = date_from_s = date_to_s = ''
    date_format = '%m/%d/%Y'

    def get_queryset(self):
        date_to_default = timezone.now()
        date_from_default = timezone.now() - timezone.timedelta(7)
        date_to_default_s = date_to_default.strftime(self.date_format)
        date_from_default_s = date_from_default.strftime(self.date_format)

        self.command = self.request.GET.get('command', '')
        self.user = self.request.GET.get('user')
        self.asset = self.request.GET.get('asset')
        self.system_user = self.request.GET.get('system_user')
        self.date_from_s = self.request.GET.get('date_from', date_from_default_s)
        self.date_to_s = self.request.GET.get('date_to', date_to_default_s)

        filter_kwargs = {}
        if self.date_from_s:
            date_from = datetime.strptime(self.date_from_s, self.date_format)
            date_from = date_from.replace(
                tzinfo=timezone.get_current_timezone()
            )
            filter_kwargs['date_from'] = date_from
        if self.date_to_s:
            date_to = timezone.datetime.strptime(
                self.date_to_s + ' 23:59:59', '%m/%d/%Y %H:%M:%S')
            date_to = date_to.replace(tzinfo=timezone.get_current_timezone())
            filter_kwargs['date_to'] = date_to
        if self.user:
            filter_kwargs['user'] = self.user
        if self.asset:
            filter_kwargs['asset'] = self.asset
        if self.system_user:
            filter_kwargs['system_user'] = self.system_user
        if self.command:
            filter_kwargs['input'] = self.command
        if filter_kwargs:
            self.queryset = command_store.filter(**filter_kwargs)
        return self.queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Terminal'),
            'action': _('Command list'),
            'user_list': utils.get_user_list_from_cache(),
            'asset_list': utils.get_asset_list_from_cache(),
            'system_user_list': utils.get_system_user_list_from_cache(),
            'command': self.command,
            'date_from': self.date_from_s,
            'date_to': self.date_to_s,
            'user': self.user,
            'asset': self.asset,
            'system_user': self.system_user,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)






