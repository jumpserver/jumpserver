# ~*~ coding: utf-8 ~*~
#

from django.views.generic import ListView, UpdateView, DeleteView, \
    DetailView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import ugettext as _
from django.urls import reverse_lazy, reverse

from common.mixins import JSONResponseMixin
from .models import Terminal
from .forms import TerminalForm
from .hands import AdminUserRequiredMixin


class TerminalListView(LoginRequiredMixin, ListView):
    model = Terminal
    template_name = 'applications/terminal_list.html'
    form_class = TerminalForm

    def get_context_data(self, **kwargs):
        context = super(TerminalListView, self).get_context_data(**kwargs)
        context.update({
            'app': _('Terminal'),
            'action': _('Terminal list'),
            'form': self.form_class()
        })
        return context


class TerminalUpdateView(AdminUserRequiredMixin, UpdateView):
    model = Terminal
    form_class = TerminalForm
    template_name = 'applications/terminal_update.html'
    success_url = reverse_lazy('applications:terminal-list')

    def get_context_data(self, **kwargs):
        context = super(TerminalUpdateView, self).get_context_data(**kwargs)
        context.update({'app': _('Applications'), 'action': _('Update terminal')})
        return context


class TerminalDetailView(LoginRequiredMixin, DetailView):
    model = Terminal
    template_name = 'applications/terminal_detail.html'
    context_object_name = 'terminal'

    def get_context_data(self, **kwargs):
        context = super(TerminalDetailView, self).get_context_data(**kwargs)
        context.update({
            'app': _('Applications'),
            'action': _('Terminal detail')
        })
        return context


class TerminalDeleteView(AdminUserRequiredMixin, DeleteView):
    model = Terminal
    template_name = 'assets/delete_confirm.html'
    success_url = reverse_lazy('applications:applications-list')


class TerminalModelAccept(AdminUserRequiredMixin, JSONResponseMixin, UpdateView):
    model = Terminal
    form_class = TerminalForm
    template_name = 'applications/terminal_modal_test.html'

    def post(self, request, *args, **kwargs):
        print(request.POST)
        return super(TerminalModelAccept, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        terminal = form.save()
        terminal.is_accepted = True
        terminal.is_active = True
        terminal.save()
        data = {
            'success': True,
            'msg': 'success'
        }
        return self.render_json_response(data)

    def form_invalid(self, form):
        print('form.data')
        data = {
            'success': False,
            'msg': str(form.errors),
        }
        return self.render_json_response(data)


class TerminalConnectView(LoginRequiredMixin, DetailView):
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
                'redirect_url': reverse('applications:terminal-list')
            }

        kwargs.update(context)
        return super(TerminalConnectView, self).get_context_data(**kwargs)
