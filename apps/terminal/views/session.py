# -*- coding: utf-8 -*-
#

import time
from datetime import datetime

from django.views.generic import ListView, UpdateView, DeleteView, DetailView, TemplateView
from django.views.generic.edit import SingleObjectMixin
from django.utils.translation import ugettext as _
from django.utils import timezone
from django.utils.module_loading import import_string
from django.urls import reverse_lazy
from django.http import HttpResponse
from django.conf import settings
from django.db.models import Q

from users.utils import AdminUserRequiredMixin
from ..models import Session, Command, Terminal
from ..backends import get_command_store
from .. import utils


__all__ = [
    'SessionOnlineListView', 'SessionOfflineListView',
    'SessionDetailView',
]

command_store = get_command_store()


class SessionListView(AdminUserRequiredMixin, ListView):
    model = Session
    template_name = 'terminal/session_list.html'
    context_object_name = 'session_list'
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    user = asset = system_user = date_from_s = date_to_s = ''
    date_format = '%m/%d/%Y'

    def get_queryset(self):
        date_to_default = timezone.now()
        date_from_default = timezone.now() - timezone.timedelta(7)
        date_to_default_s = date_to_default.strftime(self.date_format)
        date_from_default_s = date_from_default.strftime(self.date_format)

        self.queryset = super().get_queryset()
        self.user = self.request.GET.get('user')
        self.asset = self.request.GET.get('asset')
        self.system_user = self.request.GET.get('system_user')
        self.date_from_s = self.request.GET.get('date_from', date_from_default_s)
        self.date_to_s = self.request.GET.get('date_to', date_to_default_s)

        filter_kwargs = {}
        if self.date_from_s:
            date_from = datetime.strptime(self.date_from_s, self.date_format)
            date_from = date_from.replace(tzinfo=timezone.get_current_timezone())
            filter_kwargs['date_start__gt'] = date_from
        if self.date_to_s:
            date_to = timezone.datetime.strptime(
                self.date_to_s + ' 23:59:59', '%m/%d/%Y %H:%M:%S')
            date_to = date_to.replace(tzinfo=timezone.get_current_timezone())
            filter_kwargs['date_start__lt'] = date_to
        if self.user:
            filter_kwargs['user'] = self.user
        if self.asset:
            filter_kwargs['asset'] = self.asset
        if self.system_user:
            filter_kwargs['system_user'] = self.system_user
        if filter_kwargs:
            self.queryset = self.queryset.filter(**filter_kwargs)
        return self.queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Audits'),
            'action': _('Proxy log list'),
            'user_list': utils.get_user_list_from_cache(),
            'asset_list': utils.get_asset_list_from_cache(),
            'system_user_list': utils.get_system_user_list_from_cache(),
            'date_from': self.date_from_s,
            'date_to': self.date_to_s,
            'user': self.user,
            'asset': self.asset,
            'system_user': self.system_user,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class SessionOnlineListView(SessionListView):

    def get_queryset(self):
        queryset = super().get_queryset().filter(is_finished=False)
        return queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Terminal'),
            'action': _('Session online list'),
            'now': timezone.now(),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class SessionOfflineListView(SessionListView):

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(is_finished=True)
        return queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Terminal'),
            'action': _('Session offline list'),
            'now': timezone.now(),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class SessionDetailView(SingleObjectMixin, ListView):
    template_name = 'terminal/session_detail.html'
    model = Session

    def get_queryset(self):
        self.object = self.get_object(self.model.objects.all())
        return command_store.filter(session=self.object.id)

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Terminal'),
            'action': _('Session detail'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

