# -*- coding: utf-8 -*-
#

from django.views.generic import View, TemplateView
from django.utils.translation import ugettext as _
from django.http import HttpResponse
from django.template import loader
from django.utils import timezone
import time

from common.mixins import DatetimeSearchMixin
from common.permissions import PermissionsMixin, IsOrgAdmin, IsAuditor
from ..backends import get_multi_command_storage

__all__ = ['CommandListView']
common_storage = get_multi_command_storage()


class CommandListView(DatetimeSearchMixin, PermissionsMixin, TemplateView):
    template_name = "terminal/command_list.html"
    permission_classes = [IsOrgAdmin | IsAuditor]
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

