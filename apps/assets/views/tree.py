# -*- coding: utf-8 -*-
#

from django.views.generic import TemplateView
from django.utils.translation import ugettext_lazy as _

from common.mixins import AdminUserRequiredMixin


__all__ = ['TreeView']


class TreeView(AdminUserRequiredMixin, TemplateView):
    template_name = 'assets/tree.html'

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Assets'),
            'action': _('Tree view'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

