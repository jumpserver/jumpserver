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


__all__ = [
    'SessionOnlineListView', 'SessionOfflineListView',
    'SessionDetailView',
]

command_store = get_command_store()


class SessionListView(AdminUserRequiredMixin, ListView):
    model = Session
    template_name = 'terminal/session_online.html'
    context_object_name = 'session_list'
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    keyword = username = hostname = system_user = date_from_s = date_to_s = ''
    ordering = ['is_finished', '-id']
    date_format = '%m/%d/%Y'

    def get_queryset(self):
        date_now = timezone.localtime(timezone.now())
        date_to_default = date_now.strftime(self.date_format)
        date_from_default = (date_now-timezone.timedelta(7)).strftime(self.date_format)

        self.queryset = super().get_queryset()
        self.keyword = self.request.GET.get('keyword', '')
        self.username = self.request.GET.get('username')
        self.ip = self.request.GET.get('ip')
        self.system_user = self.request.GET.get('system_user')
        self.date_from_s = self.request.GET.get('date_from', date_from_default)
        self.date_to_s = self.request.GET.get('date_to', date_to_default)

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
        if self.username:
            filter_kwargs['user'] = self.username
        if self.ip:
            filter_kwargs['asset'] = self.ip
        if self.system_user:
            filter_kwargs['system_user'] = self.system_user
        if self.keyword:
            self.queryset = self.queryset.filter(
                Q(user__icontains=self.keyword) |
                Q(asset__icontains=self.keyword) |
                Q(system_user__icontains=self.keyword)).distinct()
        if filter_kwargs:
            self.queryset = self.queryset.filter(**filter_kwargs)
        return self.queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Audits'),
            'action': _('Proxy log list'),
            'user_list': set(
                list(Session.objects.values_list('user', flat=True))),
            'asset_list': set(
                list(Session.objects.values_list('asset', flat=True))),
            'system_user_list': set(
                list(Session.objects.values_list('system_user', flat=True))),
            'keyword': self.keyword,
            'date_from': self.date_from_s,
            'date_to': self.date_to_s,
            'username': self.username,
            'ip': self.ip,
            'system_user': self.system_user,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class SessionOnlineListView(SessionListView):
    template_name = 'terminal/session_online.html'

    def get_queryset(self):
        queryset = super().get_queryset().filter(is_finished=False)
        return queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Terminal'),
            'action': _('Session online list'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class SessionOfflineListView(SessionListView):
    template_name = 'terminal/session_offline.html'

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(is_finished=True)
        return queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Terminal'),
            'action': _('Session offline list'),
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

