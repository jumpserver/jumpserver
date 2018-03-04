# -*- coding: utf-8 -*-
#

from django.views.generic import ListView
from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext as _

from common.mixins import DatetimeSearchMixin, AdminUserRequiredMixin
from ..models import Command
from .. import utils
from ..backends import get_multi_command_store

__all__ = ['CommandListView']
common_storage = get_multi_command_store()


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






