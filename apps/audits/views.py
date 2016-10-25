# ~*~ coding: utf-8 ~*~
#

from django.views.generic import ListView, UpdateView, DeleteView, DetailView
from django.utils.translation import ugettext as _
from django.urls import reverse_lazy

from .models import ProxyLog, CommandLog


class ProxyLogListView(ListView):
    model = ProxyLog
    template_name = 'audits/proxy_log_list.html'

    def get_context_data(self, **kwargs):
        context = super(ProxyLogListView, self).get_context_data(**kwargs)
        context.update({'app': _('Audits'), 'action': _('Proxy log list')})
        return context


class ProxyLogDetailView(DetailView):
    model = ProxyLog
    template_name = 'audits/proxy_log_detail.html'

    def get_context_data(self, **kwargs):
        context = super(ProxyLogDetailView, self).get_context_data(**kwargs)
        context.update({'app': _('Audits'), 'action': _('Proxy log detail')})

