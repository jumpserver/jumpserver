# -*- coding: utf-8 -*-
#

from django.views.generic import ListView, TemplateView
from django.views.generic.edit import SingleObjectMixin
from django.utils.translation import ugettext as _
from django.utils import timezone
from django.conf import settings

from common.permissions import PermissionsMixin, IsOrgAdmin, IsOrgAuditor
from common.mixins import DatetimeSearchMixin
from ..models import Session, Command, Terminal
from ..backends import get_multi_command_storage
from .. import utils


__all__ = [
    'SessionOnlineListView', 'SessionOfflineListView',
    'SessionDetailView',
]


class SessionListView(PermissionsMixin, TemplateView):
    model = Session
    template_name = 'terminal/session_list.html'
    date_from = date_to = None
    permission_classes = [IsOrgAdmin | IsOrgAuditor]
    default_days_ago = 5

    def get_context_data(self, **kwargs):
        now = timezone.now()
        context = {
            'date_from': now - timezone.timedelta(days=self.default_days_ago),
            'date_to': now,
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class SessionOnlineListView(SessionListView):
    def get_context_data(self, **kwargs):
        context = {
            'app': _('Sessions'),
            'action': _('Session online list'),
            'type': 'online',
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class SessionOfflineListView(SessionListView):
    def get_context_data(self, **kwargs):
        context = {
            'app': _('Sessions'),
            'action': _('Session offline'),
            'type': 'offline',
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)


class SessionDetailView(SingleObjectMixin, PermissionsMixin, ListView):
    template_name = 'terminal/session_detail.html'
    model = Session
    object = None
    permission_classes = [IsOrgAdmin | IsOrgAuditor]

    def get(self, request, *args, **kwargs):
        self.object = self.get_object(queryset=self.model.objects.all())
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        command_store = get_multi_command_storage()
        return command_store.filter(session=self.object.id)

    def get_context_data(self, **kwargs):
        context = {
            'app': _('Sessions'),
            'action': _('Session detail'),
        }
        kwargs.update(context)
        return super().get_context_data(**kwargs)

