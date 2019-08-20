# -*- coding: utf-8 -*-
#

from django.views.generic import TemplateView
from django.utils.translation import ugettext as _
from django.utils import timezone

from common.permissions import PermissionsMixin, IsOrgAdmin, IsOrgAuditor

__all__ = ['CommandListView']


class CommandListView(PermissionsMixin, TemplateView):
    template_name = "terminal/command_list.html"
    permission_classes = [IsOrgAdmin | IsOrgAuditor]
    default_days_ago = 5

    def get_context_data(self, **kwargs):
        now = timezone.now()
        context = {
            'app': _('Sessions'),
            'action': _('Command list'),
            'date_from': now - timezone.timedelta(days=self.default_days_ago),
            'date_to': now,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

