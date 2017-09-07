# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals

from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView

from django.conf import settings
from ..models import *
from django.utils.translation import ugettext as _


class ConfigListView(LoginRequiredMixin, ListView):
    model = HybrisConfig
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    template_name = 'hybris/hybris_conf.html'
    context_object_name = 'hybris_conf'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Hybris'),
            'action': _('Configuration'),
        }
        kwargs.update(context)
        return super(ConfigListView, self).get_context_data(**kwargs)


class ConfCreateView(LoginRequiredMixin, ListView):
    model = HybrisConfig
    paginate_by = settings.CONFIG.DISPLAY_PER_PAGE
    template_name = 'hybris/hybris_conf.html'
    context_object_name = 'hybris_conf'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Hybris'),
            'action': _('Configuration'),
        }
        kwargs.update(context)
        return super(ConfCreateView, self).get_context_data(**kwargs)
