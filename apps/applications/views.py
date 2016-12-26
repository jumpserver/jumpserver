# ~*~ coding: utf-8 ~*~
#

from django.views.generic import ListView, UpdateView, DeleteView, FormView
from django.utils.translation import ugettext as _
from django.urls import reverse_lazy

from .models import Terminal
from users.utils import AdminUserRequiredMixin
from common.mixins import JSONResponseMixin
from .forms import TerminalForm


class TerminalListView(ListView):
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


class TerminalUpdateView(UpdateView):
    model = Terminal
    form_class = TerminalForm
    template_name = 'applications/terminal_update.html'
    success_url = reverse_lazy('applications:applications-list')

    def get_context_data(self, **kwargs):
        context = super(TerminalUpdateView, self).get_context_data(**kwargs)
        context.update({'app': _('Terminal'), 'action': _('Update applications')})
        return context


class TerminalDeleteView(DeleteView):
    model = Terminal
    template_name = 'assets/delete_confirm.html'
    success_url = reverse_lazy('applications:applications-list')


class TerminalModelAccept(AdminUserRequiredMixin, JSONResponseMixin, UpdateView):
    model = Terminal
    form_class = TerminalForm

    def form_valid(self, form):
        terminal = form.save()
        terminal.is_accepted = True
        terminal.save()
        data = {
            'success': True,
            'msg': 'success'
        }
        print('Valid')
        return self.render_json_response(data)

    def form_invalid(self, form):
        print(form.errors)
        data = {
            'success': False,
            'msg': ','.join(form.errors)
        }
        return self.render_json_response(data)


