# ~*~ coding: utf-8 ~*~
#
from django.views.generic import ListView, UpdateView, DeleteView, \
    DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import ugettext as _
from django.shortcuts import redirect
from django.urls import reverse_lazy, reverse

from common.mixins import JSONResponseMixin
from ..models import Terminal
from ..forms import TerminalForm
from common.permissions import SuperUserRequiredMixin


__all__ = [
    "TerminalListView", "TerminalUpdateView", "TerminalDetailView",
    "TerminalDeleteView", "TerminalConnectView", "TerminalAcceptView",
    "WebTerminalView", 'WebSFTPView',
]


class TerminalListView(SuperUserRequiredMixin, ListView):
    model = Terminal
    template_name = 'terminal/terminal_list.html'
    form_class = TerminalForm

    def get_context_data(self, **kwargs):
        context = super(TerminalListView, self).get_context_data(**kwargs)
        context.update({
            'app': _('Terminal'),
            'action': _('Terminal list'),
            'form': self.form_class()
        })
        return context


class TerminalUpdateView(SuperUserRequiredMixin, UpdateView):
    model = Terminal
    form_class = TerminalForm
    template_name = 'terminal/terminal_update.html'
    success_url = reverse_lazy('terminal:terminal-list')

    def get_context_data(self, **kwargs):
        context = super(TerminalUpdateView, self).get_context_data(**kwargs)
        context.update({'app': _('Terminal'), 'action': _('Update terminal')})
        return context


class TerminalDetailView(LoginRequiredMixin, SuperUserRequiredMixin, DetailView):
    model = Terminal
    template_name = 'terminal/terminal_detail.html'
    context_object_name = 'terminal'

    def get_context_data(self, **kwargs):
        context = super(TerminalDetailView, self).get_context_data(**kwargs)
        context.update({
            'app': _('Terminal'),
            'action': _('Terminal detail')
        })
        return context


class TerminalDeleteView(SuperUserRequiredMixin, DeleteView):
    model = Terminal
    template_name = 'delete_confirm.html'
    success_url = reverse_lazy('terminal:terminal-list')


class TerminalAcceptView(SuperUserRequiredMixin, JSONResponseMixin, UpdateView):
    model = Terminal
    form_class = TerminalForm
    template_name = 'terminal/terminal_modal_accept.html'

    def form_valid(self, form):
        terminal = form.save()
        terminal.create_app_user()
        terminal.is_accepted = True
        terminal.is_active = True
        terminal.save()
        data = {
            'success': True,
            'msg': 'success'
        }
        return self.render_json_response(data)

    def form_invalid(self, form):
        data = {
            'success': False,
            'msg': str(form.errors),
        }
        return self.render_json_response(data)


class TerminalConnectView(LoginRequiredMixin, SuperUserRequiredMixin, DetailView):
    """
    Abandon
    """
    template_name = 'flash_message_standalone.html'
    model = Terminal

    def get_context_data(self, **kwargs):
        if self.object.type == 'Web':
            context = {
                'title': _('Redirect to web terminal'),
                'messages': _('Redirect to web terminal') + self.object.url,
                'auto_redirect': True,
                'interval': 3,
                'redirect_url': self.object.url
            }
        else:
            context = {
                'title': _('Connect ssh terminal'),
                'messages': _('You should use your ssh client tools '
                              'connect terminal: {} <br /> <br />'
                              '{}'.format(self.object.name, self.object.url)),
                'redirect_url': reverse('terminal:terminal-list')
            }

        kwargs.update(context)
        return super(TerminalConnectView, self).get_context_data(**kwargs)


class WebTerminalView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return redirect('/luna/?' + request.GET.urlencode())


class WebSFTPView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        return redirect('/coco/elfinder/sftp/?' + request.GET.urlencode())
