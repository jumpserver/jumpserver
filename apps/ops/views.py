# -*- coding: utf-8 -*-
#
from django.views.generic import TemplateView
from django.conf import settings

from common.permissions import PermissionsMixin, IsOrgAdmin, IsOrgAuditor


__all__ = ['CeleryTaskLogView']


class CeleryTaskLogView(PermissionsMixin, TemplateView):
    template_name = 'ops/celery_task_log.html'
    permission_classes = [IsOrgAdmin | IsOrgAuditor]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'task_id': self.kwargs.get('pk'),
            'ws_port': settings.WS_LISTEN_PORT
        })
        return context
