# -*- coding: utf-8 -*-
#
from django.conf import settings
from django.http import HttpResponse
from django.utils import translation
from django.views.generic import TemplateView

from audits.const import ActionChoices
from audits.handler import create_or_update_operate_log
from common.views.mixins import PermissionsMixin
from ops.models import CeleryTaskExecution
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
        response = super().get(request, *args, **kwargs)
        task = CeleryTaskExecution.objects.filter(id=self.kwargs.get('pk')).first()
        if task:
            with translation.override('en'):
                create_or_update_operate_log(
                    ActionChoices.view, task._meta.verbose_name,
                    force=True, resource=task,
                )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'task_id': self.kwargs.get('pk'),
            'ws_port': settings.WS_LISTEN_PORT,
            'vendor': settings.VENDOR.lower()
        })
        return context
