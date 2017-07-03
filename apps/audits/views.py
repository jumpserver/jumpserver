# ~*~ coding: utf-8 ~*~
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

from .models import ProxyLog, CommandLog, LoginLog
from .hands import User, Asset, SystemUser, AdminUserRequiredMixin
from audits.backends import command_store
from audits.backends import CommandLogSerializer


class ProxyLogListView(AdminUserRequiredMixin, ListView):
    model = ProxyLog
    template_name = 'audits/proxy_log_online_list.html'
    context_object_name = 'proxy_log_list'
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    keyword = username = hostname = system_user = date_from_s = date_to_s = ''
    ordering = ['is_finished', '-id']
    date_format = '%m/%d/%Y'

    def get_queryset(self):
        date_now = timezone.localtime(timezone.now())
        date_to_default = date_now.strftime(self.date_format)
        date_from_default = (date_now-timezone.timedelta(7))\
            .strftime(self.date_format)

        self.queryset = super(ProxyLogListView, self).get_queryset()
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
                list(ProxyLog.objects.values_list('user', flat=True))),
            'asset_list': set(
                list(ProxyLog.objects.values_list('asset', flat=True))),
            'system_user_list': set(
                list(ProxyLog.objects.values_list('system_user', flat=True))),
            'keyword': self.keyword,
            'date_from': self.date_from_s,
            'date_to': self.date_to_s,
            'username': self.username,
            'ip': self.ip,
            'system_user': self.system_user,
        }
        kwargs.update(context)
        return super(ProxyLogListView, self).get_context_data(**kwargs)


class ProxyLogOfflineListView(ProxyLogListView):
    template_name = 'audits/proxy_log_offline_list.html'

    def get_queryset(self):
        queryset = super(ProxyLogOfflineListView, self).get_queryset()
        queryset = queryset.filter(is_finished=True)
        return queryset

    def get_context_data(self, **kwargs):
        context = {
            'action': _('Proxy log offline list'),
        }
        kwargs.update(context)
        return super(ProxyLogOfflineListView, self).get_context_data(**kwargs)


class ProxyLogOnlineListView(ProxyLogListView):
    template_name = 'audits/proxy_log_online_list.html'

    def get_queryset(self):
        queryset = super(ProxyLogOnlineListView, self).get_queryset()
        queryset = queryset.filter(is_finished=False)
        return queryset

    def get_context_data(self, **kwargs):
        context = {
            'action': _('Proxy log online list'),
        }
        kwargs.update(context)
        return super(ProxyLogOnlineListView, self).get_context_data(**kwargs)


class ProxyLogDetailView(AdminUserRequiredMixin,
                         SingleObjectMixin,
                         ListView):
    template_name = 'audits/proxy_log_detail.html'
    context_object_name = 'proxy_log'
    object = ''

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=ProxyLog.objects.all())
        return super(ProxyLogDetailView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        return list(command_store.filter(proxy_log_id=self.object.id))

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Audits',
            'action': 'Proxy log detail',
        }
        kwargs.update(context)
        return super(ProxyLogDetailView, self).get_context_data(**kwargs)


# class ProxyLogCommandsListView(AdminUserRequiredMixin,
#                                SingleObjectMixin,
#                                ListView):
#     template_name = 'audits/proxy_log_commands_list_modal.html'
#     object = ''
#
#     def get(self, request, *args, **kwargs):
#         self.object = self.get_object(queryset=ProxyLog.objects.all())
#         return super(ProxyLogCommandsListView, self).\
#             get(request, *args, **kwargs)
#
#     def get_queryset(self):
#         return list(self.object.command_log.all())


class CommandLogListView(AdminUserRequiredMixin, ListView):
    template_name = 'audits/command_log_list.html'
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    context_object_name = 'command_list'
    username = ip = system_user = command = date_from_s = date_to_s = ''
    date_format = '%m/%d/%Y'
    ordering = ['-id']

    def get_queryset(self):
        date_now = timezone.localtime(timezone.now())
        date_to_default = date_now.strftime(self.date_format)
        date_from_default = (date_now - timezone.timedelta(7)) \
            .strftime(self.date_format)
        self.command = self.request.GET.get('command', '')
        self.username = self.request.GET.get('username')
        self.ip = self.request.GET.get('ip')
        self.system_user = self.request.GET.get('system_user')
        self.date_from_s = \
            self.request.GET.get('date_from', date_from_default)
        self.date_to_s = \
            self.request.GET.get('date_to', date_to_default)

        filter_kwargs = {}
        if self.date_from_s:
            date_from = datetime.strptime(self.date_from_s, self.date_format)\
                .replace(tzinfo=timezone.get_current_timezone())
            # date_from_utc = date_from.astimezone(pytz.utc)
            date_from_ts = time.mktime(date_from.timetuple())
            filter_kwargs['date_from_ts'] = date_from_ts
        if self.date_to_s:
            date_to = datetime.strptime(
                self.date_to_s + ' 23:59:59', '%m/%d/%Y %H:%M:%S')\
                .replace(tzinfo=timezone.get_current_timezone())
            date_to_ts = time.mktime(date_to.timetuple())
            filter_kwargs['date_to_ts'] = date_to_ts
        if self.username:
            filter_kwargs['user'] = self.username
        if self.ip:
            filter_kwargs['asset'] = self.ip
        if self.system_user:
            filter_kwargs['system_user'] = self.system_user
        if self.command:
            filter_kwargs['command'] = self.command
        self.queryset = command_store.filter(**filter_kwargs).order_by(*self.ordering)
        return self.queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Audits'),
            'action': _('Command log list'),
            'user_list': User.objects.all().order_by('username'),
            'asset_list': Asset.objects.all().order_by('ip'),
            'system_user_list': SystemUser.objects.all().order_by('username'),
            'command': self.command,
            'date_from': self.date_from_s,
            'date_to': self.date_to_s,
            'username': self.username,
            'ip': self.ip,
            'system_user': self.system_user,
        }
        kwargs.update(context)
        return super(CommandLogListView, self).get_context_data(**kwargs)


class LoginLogListView(AdminUserRequiredMixin, ListView):
    model = LoginLog
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    template_name = 'audits/login_log_list.html'
    context_object_name = 'login_log_list'
    keyword = username = date_from_s = date_to_s = ''

    def get_queryset(self):
        date_now = timezone.localtime(timezone.now())
        now_s = date_now.strftime('%m/%d/%Y')
        seven_days_ago_s = (date_now - timezone.timedelta(7))\
            .strftime('%m/%d/%Y')
        self.queryset = super(LoginLogListView, self).get_queryset()
        self.keyword = keyword = self.request.GET.get('keyword', '')
        self.username = username = self.request.GET.get('username', '')
        self.date_from_s = date_from_s = self.request.GET.get(
            'date_from', '%s' % seven_days_ago_s)
        self.date_to_s = date_to_s = self.request.GET.get(
            'date_to', '%s' % now_s)

        if date_from_s:
            date_from = timezone.datetime.strptime(date_from_s, '%m/%d/%Y')
            self.queryset = self.queryset.filter(date_login__gt=date_from)
        if date_to_s:
            date_to = timezone.datetime.strptime(
                date_to_s + ' 23:59:59', '%m/%d/%Y %H:%M:%S')
            self.queryset = self.queryset.filter(date_login__lt=date_to)
        if username:
            self.queryset = self.queryset.filter(username=username)
        if keyword:
            self.queryset = self.queryset.filter(
                Q(username__contains=keyword) |
                Q(name__icontains=keyword) |
                Q(login_ip=keyword)).distinct()
        return self.queryset

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Audits'),
            'action': _('Proxy log list'),
            'user_list': User.objects.all().order_by('username'),
            'keyword': self.keyword,
            'date_from': self.date_from_s,
            'date_to': self.date_to_s,
            'username': self.username,
        }
        kwargs.update(context)
        return super(LoginLogListView, self).get_context_data(**kwargs)
