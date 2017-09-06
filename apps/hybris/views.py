# ~*~ coding: utf-8 ~*~
from __future__ import unicode_literals
from django.views.generic import ListView
from .models import HybrisConfig
from django.utils.translation import ugettext as _


class HybrisConfView(ListView):
    model = HybrisConfig
    template_name = 'hybris/hybris_configuration.html'

    def get_context_data(self, **kwargs):
        context = {
            'app':  _('Hybris'),
            'action': _('Configuration'),
            # 'date_from': self.date_from_s,
            # 'date_to': self.date_to_s,
            # 'keyword': self.keyword,
        }
        kwargs.update(context)
        return super(HybrisConfView, self).get_context_data(**kwargs)
