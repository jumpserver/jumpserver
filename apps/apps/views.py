# ~*~ coding: utf-8 ~*~
#

from django.views.generic import ListView
from django.utils.translation import ugettext as _

from .models import Terminal


class TerminalListView(ListView):
    model = Terminal
    template_name = 'apps/terminal_list.html'

    def get_context_data(self, **kwargs):
        context = super(TerminalListView, self).get_context_data(**kwargs)
        context.update({'app': _('Terminal'), 'action': _('Terminal list')})
        return context
