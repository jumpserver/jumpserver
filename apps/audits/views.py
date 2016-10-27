# ~*~ coding: utf-8 ~*~
#

from django.views.generic import ListView, UpdateView, DeleteView, DetailView, TemplateView
from django.views.generic.edit import SingleObjectMixin
from django.utils.translation import ugettext as _
from django.urls import reverse_lazy
from django.conf import settings

from .models import ProxyLog, CommandLog
from .utils import AdminUserRequiredMixin


class ProxyLogListView(TemplateView):
    template_name = 'audits/proxy_log_list.html'

    def get_context_data(self, **kwargs):
        context = super(ProxyLogListView, self).get_context_data(**kwargs)
        context.update({'app': _('Audits'), 'action': _('Proxy log list')})
        return context


class ProxyLogDetailView(AdminUserRequiredMixin, SingleObjectMixin, ListView):
    template_name = 'audits/proxy_log_detail.html'
    context_object_name = 'proxy_log'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=ProxyLog.objects.all())
        return super(ProxyLogDetailView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        return list(self.object.command_log.all())

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Audits',
            'action': 'Proxy log detail',
        }
        kwargs.update(context)
        return super(ProxyLogDetailView, self).get_context_data(**kwargs)


class ProxyLogCommandsListView(AdminUserRequiredMixin, SingleObjectMixin, ListView):
    template_name = 'audits/proxy_log_commands_list_modal.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=ProxyLog.objects.all())
        return super(ProxyLogCommandsListView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        return list(self.object.command_log.all())


class CommandLogListView(AdminUserRequiredMixin, TemplateView):
    template_name = 'audits/command_log_list.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': 'Audits',
            'action': 'Command log list'
        }
        kwargs.update(context)
        return super(CommandLogListView, self).get_context_data(**kwargs)
