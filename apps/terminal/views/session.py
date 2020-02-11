# -*- coding: utf-8 -*-
#
import os

from django.views.generic import ListView, TemplateView, DetailView
from django.views.generic.edit import SingleObjectMixin
from django.utils.translation import ugettext as _
from django.utils import timezone
from django.utils.encoding import escape_uri_path
from django.http import FileResponse
from django.core.files.storage import default_storage

from common.permissions import PermissionsMixin, IsOrgAdmin, IsOrgAuditor
from ..models import Session
from ..backends import get_multi_command_storage
from .. import utils


__all__ = [
    'SessionOnlineListView', 'SessionOfflineListView',
    'SessionDetailView', 'SessionReplayDownloadView',
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


class SessionReplayDownloadView(PermissionsMixin, DetailView):
    permission_classes = [IsOrgAdmin | IsOrgAuditor]
    model = Session

    def get(self, request, *args, **kwargs):
        session = self.get_object()
        local_path, url = utils.get_session_replay_url(session)
        full_path = default_storage.path(local_path)
        file = open(full_path, 'rb')
        response = FileResponse(file)
        response['Content-Type'] = 'application/octet-stream'
        # 这里要注意哦，网上查到的方法都是response['Content-Disposition']='attachment;filename="filename.py"',
        # 但是如果文件名是英文名没问题，如果文件名包含中文，下载下来的文件名会被改为url中的path。
        filename = escape_uri_path(os.path.basename(local_path))
        disposition = "attachment; filename*=UTF-8''{}".format(filename)
        response["Content-Disposition"] = disposition
        return response
