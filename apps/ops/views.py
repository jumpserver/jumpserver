# -*- coding: utf-8 -*-
#
from django.conf import settings
from django.http import HttpResponse
from django.views.generic import TemplateView

from common.views.mixins import PermissionsMixin
from rbac.permissions import RBACPermission

__all__ = ['CeleryTaskLogView']


class CeleryTaskLogView(PermissionsMixin, TemplateView):
    template_name = 'ops/celery_task_log.html'
    permission_classes = [RBACPermission]
    rbac_perms = {
        'GET': 'ops.view_celerytaskexecution'
    }

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponse(status=401)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'task_id': self.kwargs.get('pk'),
            'ws_port': settings.WS_LISTEN_PORT
        })
        return context
